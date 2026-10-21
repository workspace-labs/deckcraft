"""Bounded, local-only Chromium screenshots using the standard-library CDP client.

A full-page picture keeps a normal viewport: making the browser window thousands
of pixels tall changes vh-based designs. No driver, server or dependency is added.
"""
import base64
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import signal
import socket
import struct
import subprocess
import time
from urllib.parse import urlsplit


class BrowserError(subprocess.SubprocessError):
    """The owned browser did not produce a verified fresh screenshot."""


class _WebSocket:
    GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    MAX_MESSAGE = 64 * 1024 * 1024

    def __init__(self, url, port, timeout=60):
        u = urlsplit(url)
        if (u.scheme != "ws" or u.hostname != "127.0.0.1" or u.port != port or
                u.username or u.password or not u.path.startswith("/devtools/page/") or u.query or u.fragment):
            raise BrowserError("The browser debugger must stay on its own loopback port.")
        self.timeout, self.buffer = timeout, b""
        self.socket = socket.create_connection(("127.0.0.1", port), timeout=timeout)
        try:
            key = base64.b64encode(os.urandom(16)).decode("ascii")
            request = (f"GET {u.path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nUpgrade: websocket\r\n"
                       f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
            self.socket.sendall(request.encode("ascii"))
            deadline = time.monotonic() + timeout
            while b"\r\n\r\n" not in self.buffer:
                if len(self.buffer) > 16384:
                    raise BrowserError("The browser handshake is too large.")
                self.buffer += self._chunk(4096, deadline)
            header, self.buffer = self.buffer.split(b"\r\n\r\n", 1)
            lines = header.decode("ascii").split("\r\n")
            fields = {key.strip().lower(): value.strip() for key, value in
                      (line.split(":", 1) for line in lines[1:] if ":" in line)}
            expected = base64.b64encode(hashlib.sha1((key + self.GUID).encode("ascii")).digest()).decode("ascii")
            if (lines[0].split()[1:2] != ["101"] or
                    fields.get("sec-websocket-accept", "") != expected):
                raise BrowserError("The browser refused its local debugger handshake.")
        except Exception:
            self.close()
            raise

    def _chunk(self, n, deadline):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise BrowserError("The browser debugger timed out.")
        self.socket.settimeout(remaining)
        try:
            data = self.socket.recv(n)
        except OSError as e:
            raise BrowserError("The browser debugger stopped responding.") from e
        if not data:
            raise BrowserError("The browser debugger closed unexpectedly.")
        return data

    def _read(self, n, deadline):
        while len(self.buffer) < n:
            self.buffer += self._chunk(min(65536, n - len(self.buffer)), deadline)
        data, self.buffer = self.buffer[:n], self.buffer[n:]
        return data

    def send(self, data, opcode=1):
        if isinstance(data, str):
            data = data.encode("utf-8")
        n, mask = len(data), os.urandom(4)
        if n > self.MAX_MESSAGE:
            raise BrowserError("The browser command is too large.")
        header = bytes([0x80 | opcode])
        header += (bytes([0x80 | n]) if n < 126 else bytes([0xFE]) + struct.pack("!H", n)
                   if n < 65536 else bytes([0xFF]) + struct.pack("!Q", n))
        self.socket.sendall(header + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(data)))

    def receive(self, timeout=None):
        deadline = time.monotonic() + (timeout or self.timeout)
        parts, total, started = [], 0, False
        while True:
            a, b = self._read(2, deadline)
            final, opcode, n = bool(a & 128), a & 15, b & 127
            if a & 0x70 or b & 128:
                raise BrowserError("The browser sent an invalid debugger frame.")
            if n == 126:
                n = struct.unpack("!H", self._read(2, deadline))[0]
            elif n == 127:
                n = struct.unpack("!Q", self._read(8, deadline))[0]
            if n > self.MAX_MESSAGE or total + n > self.MAX_MESSAGE:
                raise BrowserError("The browser response is too large.")
            if opcode >= 8 and (not final or n > 125):
                raise BrowserError("The browser sent an invalid control frame.")
            data = self._read(n, deadline)
            if opcode == 8:
                raise BrowserError("The browser debugger closed unexpectedly.")
            if opcode == 9:
                self.send(data, opcode=10)
                continue
            if opcode == 10:
                continue
            if opcode == 1 and not started:
                started = True
            elif opcode != 0 or not started:
                raise BrowserError("The browser sent an invalid continuation frame.")
            parts.append(data)
            total += n
            if final:
                try:
                    value = json.loads(b"".join(parts).decode("utf-8"))
                except (ValueError, UnicodeError) as e:
                    raise BrowserError("The browser sent an invalid debugger message.") from e
                if not isinstance(value, dict):
                    raise BrowserError("The browser sent an invalid debugger response.")
                return value

    def close(self):
        self.socket.close()


class BrowserSession:
    """One hidden browser owned by this check; the caller owns its temp profile."""
    MAX_DIMENSION = 32767
    MAX_PIXELS = 128 * 1024 * 1024

    def __init__(self, browser, profile):
        self.browser, self.profile = browser, Path(profile)
        self.process = self.connection = None
        self.events, self.serial = [], 0

    def __enter__(self):
        port_file = self.profile / "DevToolsActivePort"
        if port_file.exists():
            raise BrowserError("The browser profile must be fresh.")
        try:
            options = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
                       else {"start_new_session": True})
            self.process = subprocess.Popen([
                self.browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                "--no-default-browser-check", "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=0",
                "--user-data-dir=" + str(self.profile), "about:blank"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
            deadline = time.monotonic() + 15
            while not port_file.exists():
                if self.process.poll() is not None or time.monotonic() >= deadline:
                    raise BrowserError("The hidden browser did not start its local debugger.")
                time.sleep(0.025)
            port = int(port_file.read_text(encoding="utf-8").splitlines()[0])
            client = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            try:
                client.request("GET", "/json/list")
                response = client.getresponse()
                data = response.read(1024 * 1024 + 1)
                if response.status != 200 or len(data) > 1024 * 1024:
                    raise BrowserError("The browser did not list its local page.")
                tabs = json.loads(data)
            finally:
                client.close()
            endpoint = next(t["webSocketDebuggerUrl"] for t in tabs if t.get("type") == "page")
            self.connection = _WebSocket(endpoint, port)
            self._command("Page.enable")
            return self
        except Exception as e:
            self.close()
            raise BrowserError("The hidden browser could not be connected.") from e

    def _command(self, method, params=None, timeout=60):
        self.serial += 1
        expected = self.serial
        self.connection.send(json.dumps({"id": expected, "method": method, "params": params or {}}))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            response = self.connection.receive(timeout=max(0.001, deadline - time.monotonic()))
            if response.get("id") == expected:
                if "error" in response:
                    raise BrowserError("The browser refused " + method + ".")
                return response.get("result", {})
            if "method" in response:
                self.events.append(response)
                self.events = self.events[-1000:]
        raise BrowserError("The browser command timed out.")

    def _wait_event(self, method, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            for i, event in enumerate(self.events):
                if event.get("method") == method:
                    return self.events.pop(i)
            response = self.connection.receive(timeout=max(0.001, deadline - time.monotonic()))
            if "method" in response:
                self.events.append(response)
                self.events = self.events[-1000:]
        raise BrowserError("The browser page did not finish loading.")

    def _evaluate(self, expression):
        result = self._command("Runtime.evaluate", {"expression": expression, "awaitPromise": True,
                                                    "returnByValue": True})
        if "exceptionDetails" in result:
            raise BrowserError("The browser could not inspect the loaded page.")
        return result.get("result", {}).get("value")

    def shoot(self, url, out, width, height, full_page=False):
        self._command("Emulation.setDeviceMetricsOverride", {"width": width, "height": height,
                                                             "deviceScaleFactor": 1, "mobile": False})
        self.events.clear()
        navigation = self._command("Page.navigate", {"url": url})
        if navigation.get("errorText"):
            raise BrowserError("The browser could not load the local file.")
        if "loaderId" not in navigation:
            # A hash change otherwise keeps the previous slide's initialized UI.
            self._command("Page.reload")
        self._wait_event("Page.loadEventFired")
        # Pictures show settled content, even when the page has an entrance fade.
        # Never await animation completion: decorative loops may run forever.
        self._evaluate("document.fonts.ready.then(()=>{document.getAnimations().forEach(a=>{"
                       "if(!a.effect||!Number.isFinite(a.effect.getComputedTiming().endTime)){a.cancel();return;}"
                       "try{a.finish();}catch(e){a.cancel();}});"
                       "return new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));})")
        capture_width, capture_height = width, height
        if full_page:
            metrics = self._command("Page.getLayoutMetrics")
            size = metrics.get("cssContentSize") or metrics.get("contentSize") or {}
            capture_width = math.ceil(max(width, size.get("width", width)))
            capture_height = math.ceil(max(height, size.get("height", height)))
        if (capture_width > self.MAX_DIMENSION or capture_height > self.MAX_DIMENSION or
                capture_width * capture_height > self.MAX_PIXELS):
            raise BrowserError("The page is too large for one reliable check picture.")
        result = self._command("Page.captureScreenshot", {"format": "png", "fromSurface": True,
            "captureBeyondViewport": True, "clip": {"x": 0, "y": 0, "width": capture_width,
                                                     "height": capture_height, "scale": 1}})
        try:
            image = base64.b64decode(result["data"], validate=True)
        except (KeyError, ValueError) as e:
            raise BrowserError("The browser did not return a screenshot.") from e
        Path(out).write_bytes(image)

    def close(self):
        try:
            if self.connection is not None:
                try:
                    self._command("Browser.close", timeout=5)
                except (OSError, BrowserError):
                    pass
                self.connection.close()
                self.connection = None
        finally:
            if self.process is not None:
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    try:
                        if os.name == "nt":
                            subprocess.run(["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
                        else:
                            os.killpg(self.process.pid, signal.SIGKILL)
                    except (OSError, subprocess.SubprocessError):
                        if self.process.poll() is None:
                            self.process.kill()
                    finally:
                        self.process.wait(timeout=10)
                self.process = None

    def __exit__(self, *exc):
        self.close()
