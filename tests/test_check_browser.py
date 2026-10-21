"""Browser protocol tests need only the standard library; real Chrome is opt-in."""
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock

import helpers
from deckcraft.check_browser import BrowserError, BrowserSession, _WebSocket


def frame(data, opcode=1, final=True):
    data = data.encode() if isinstance(data, str) else data
    n = len(data)
    h = bytes([(128 if final else 0) | opcode, n]) if n < 126 else bytes([
        (128 if final else 0) | opcode, 126]) + struct.pack("!H", n)
    return h + data


class FakeSocket:
    def __init__(self, messages=b""):
        key = base64.b64encode(b"k" * 16).decode()
        accept = base64.b64encode(hashlib.sha1((key + _WebSocket.GUID).encode()).digest()).decode()
        self.data = ("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                     "Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept + "\r\n\r\n").encode() + messages
        self.sent = []
        self.closed = False

    def recv(self, n):
        out, self.data = self.data[:n], self.data[n:]
        return out

    def sendall(self, data):
        self.sent.append(data)

    def settimeout(self, value):
        pass

    def close(self):
        self.closed = True


class WebSocketTests(unittest.TestCase):
    def connect(self, messages=b""):
        sock = FakeSocket(messages)
        with mock.patch("deckcraft.check_browser.socket.create_connection", return_value=sock), \
                mock.patch("deckcraft.check_browser.os.urandom", side_effect=lambda n: b"k" * n):
            ws = _WebSocket("ws://127.0.0.1:9222/devtools/page/test", 9222, timeout=1)
        return ws, sock

    def test_continuations_and_ping_preserve_json_message(self):
        ws, sock = self.connect(frame('{"id":', final=False) + frame(b"hi", opcode=9) +
                                frame('7,"result":{}}', opcode=0))
        self.assertEqual(ws.receive(), {"id": 7, "result": {}})
        self.assertEqual(sock.sent[-1][0], 0x8A)  # masked pong, not a second browser command
        self.assertTrue(sock.sent[-1][1] & 128)

    def test_truncated_message_fails_instead_of_hanging(self):
        ws, _ = self.connect(bytes([0x81, 10]) + b"short")
        with self.assertRaises(BrowserError):
            ws.receive()

    def test_oversized_payload_is_refused_before_reading_it(self):
        ws, _ = self.connect(bytes([0x81, 127]) + struct.pack("!Q", _WebSocket.MAX_MESSAGE + 1))
        with self.assertRaises(BrowserError):
            ws.receive()

    def test_remote_endpoint_is_refused_before_connecting(self):
        with mock.patch("deckcraft.check_browser.socket.create_connection") as connect:
            with self.assertRaises(BrowserError):
                _WebSocket("ws://example.com:9222/devtools/page/test", 9222)
            connect.assert_not_called()

    def test_non_page_debugger_path_is_refused(self):
        with mock.patch("deckcraft.check_browser.socket.create_connection") as connect:
            with self.assertRaises(BrowserError):
                _WebSocket("ws://127.0.0.1:9222/not-the-owned-page", 9222)
            connect.assert_not_called()

    def test_bad_handshake_is_refused(self):
        sock = FakeSocket()
        sock.data = sock.data.replace(b"Sec-WebSocket-Accept:", b"Wrong-Header:")
        with mock.patch("deckcraft.check_browser.socket.create_connection", return_value=sock), \
                mock.patch("deckcraft.check_browser.os.urandom", side_effect=lambda n: b"k" * n):
            with self.assertRaises(BrowserError):
                _WebSocket("ws://127.0.0.1:9222/devtools/page/test", 9222)
        self.assertTrue(sock.closed)


class BrowserSessionTests(unittest.TestCase):
    def session(self, size=(1280, 2400), same_document=False):
        session = BrowserSession.__new__(BrowserSession)
        session.events = []
        session._wait_event = mock.Mock()
        session._evaluate = mock.Mock(return_value=None)
        session._command = mock.Mock(side_effect=lambda name, params=None, **kwargs: {
            "Page.navigate": {} if same_document else {"loaderId": "new-document"},
            "Page.getLayoutMetrics": {"cssContentSize": {"width": size[0], "height": size[1]}},
            "Page.captureScreenshot": {"data": base64.b64encode(b"fake-png").decode()},
        }.get(name, {}))
        return session

    def test_full_page_keeps_viewport_900_and_captures_content_height(self):
        session = self.session()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "page.png"
            session.shoot("file:///page.html", path, 1280, 900, full_page=True)
            self.assertEqual(path.read_bytes(), b"fake-png")
        calls = session._command.call_args_list
        viewport = next(c.args[1] for c in calls if c.args[0] == "Emulation.setDeviceMetricsOverride")
        capture = next(c.args[1] for c in calls if c.args[0] == "Page.captureScreenshot")
        self.assertEqual((viewport["width"], viewport["height"]), (1280, 900))
        self.assertEqual(capture["clip"], {"x": 0, "y": 0, "width": 1280, "height": 2400, "scale": 1})
        self.assertTrue(capture["captureBeyondViewport"])

    def test_phone_uses_true_390_pixel_viewport(self):
        session = self.session(size=(390, 2700))
        with tempfile.TemporaryDirectory() as folder:
            session.shoot("file:///page.html", Path(folder) / "phone.png", 390, 900, full_page=True)
        viewport = session._command.call_args_list[0].args[1]
        self.assertEqual((viewport["width"], viewport["height"]), (390, 900))

    def test_same_document_slide_fragment_is_reloaded(self):
        session = self.session(same_document=True)
        with tempfile.TemporaryDirectory() as folder:
            session.shoot("file:///slides.html#2", Path(folder) / "slide.png", 1600, 900)
        self.assertTrue(any(c.args[0] == "Page.reload" for c in session._command.call_args_list))

    def test_unbounded_content_is_refused_without_publishing_a_picture(self):
        session = self.session(size=(1280, 1000000))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "page.png"
            with self.assertRaises(BrowserError):
                session.shoot("file:///page.html", path, 1280, 900, full_page=True)
            self.assertFalse(path.exists())

    def test_close_stops_only_its_owned_browser_and_closes_socket(self):
        session = BrowserSession.__new__(BrowserSession)
        connection = session.connection = mock.Mock()
        process = session.process = mock.Mock()
        session._command = mock.Mock()
        session.close()
        session._command.assert_called_once_with("Browser.close", timeout=5)
        connection.close.assert_called_once()
        process.wait.assert_called_once_with(timeout=10)
        process.terminate.assert_not_called()

    def test_close_timeout_kills_only_the_owned_process_group(self):
        import subprocess
        session = BrowserSession.__new__(BrowserSession)
        session.connection = None
        process = session.process = mock.Mock(pid=24680)
        process.wait.side_effect = [subprocess.TimeoutExpired("chrome", 10), 0]
        with mock.patch("deckcraft.check_browser.os.name", "posix"), \
                mock.patch("deckcraft.check_browser.os.killpg") as kill:
            session.close()
        kill.assert_called_once_with(24680, __import__("signal").SIGKILL)
        process.kill.assert_not_called()


BROWSER = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


@unittest.skipUnless(os.environ.get("DECKCRAFT_BROWSER_TESTS") == "1" and os.path.exists(BROWSER),
                     "opt-in local Chrome integration test")
class RealBrowserTests(unittest.TestCase):
    def test_capture_finishes_fades_and_cancels_infinite_animations(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            page = root / "animated.html"
            page.write_text('<style>.fade{animation:appear 60s linear both}'
                            '.loop{animation:appear 1s linear infinite}'
                            '@keyframes appear{from{opacity:.4}to{opacity:1}}</style>'
                            '<div class="fade">Slide content</div>'
                            '<div class="loop">Looping decoration</div>', encoding="utf-8")
            profile = root / "profile"
            profile.mkdir()
            with BrowserSession(BROWSER, str(profile)) as session:
                session.shoot(page.as_uri(), root / "settled.png", 1600, 900)
                state = session._evaluate('({opacity:getComputedStyle(document.querySelector(".fade")).opacity,'
                                          'running:document.getAnimations().filter(a=>a.playState==="running").length})')
                self.assertEqual(state, {"opacity": "1", "running": 0})

    def test_80vh_hero_is_measured_at_900px_not_at_full_page_height(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            page = root / "page.html"
            page.write_text('<style>body{margin:0}.hero{height:80vh;background:#abc}'
                            '.tail{height:1600px}</style><section class="hero"></section>'
                            '<div class="tail"></div>', encoding="utf-8")
            profile = root / "profile"
            profile.mkdir()
            with BrowserSession(BROWSER, str(profile)) as session:
                if os.name == "posix":
                    self.assertEqual(os.getpgid(session.process.pid), session.process.pid)
                session.shoot(page.as_uri(), root / "desktop.png", 1280, 900, full_page=True)
                height = session._evaluate('document.querySelector("section").getBoundingClientRect().height')
                self.assertEqual(height, 720)
                width, height = struct.unpack("!II", (root / "desktop.png").read_bytes()[16:24])
                self.assertEqual((width, height), (1280, 2320))
                session.shoot(page.as_uri(), root / "phone.png", 390, 900, full_page=True)
                width, height = struct.unpack("!II", (root / "phone.png").read_bytes()[16:24])
                self.assertEqual((width, height), (390, 2320))


if __name__ == "__main__":
    unittest.main()
