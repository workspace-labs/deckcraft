"""Take a picture of every slide and page that was made, for the agent to look at.

HTML slides and web pages: a Chrome-family browser in headless mode.
PowerPoint: LibreOffice turns it into a PDF, then pdftoppm (if present) into pictures.
Nothing is installed; a missing tool is reported in plain words.
"""
import glob
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile

from .check_browser import BrowserSession

BROWSERS = {
    "darwin": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
               "/Applications/Chromium.app/Contents/MacOS/Chromium",
               "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
               "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
    "win32": [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"],
    "linux": [],
}
LINUX_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge"]
OFFICE = {"darwin": ["/Applications/LibreOffice.app/Contents/MacOS/soffice"],
          "win32": [r"C:\Program Files\LibreOffice\program\soffice.exe"], "linux": []}


def find_browser():
    env = os.environ.get("DECKCRAFT_CHROME")
    if env and os.path.exists(env):
        return env
    for p in BROWSERS.get(_platform(), []):
        if os.path.exists(p):
            return p
    for name in LINUX_NAMES:
        p = shutil.which(name)
        if p:
            return p
    return None


def find_office():
    for name in ("soffice", "libreoffice"):
        p = shutil.which(name)
        if p:
            return p
    for p in OFFICE.get(_platform(), []):
        if os.path.exists(p):
            return p
    return None


def _platform():
    return "win32" if sys.platform.startswith("win") else ("darwin" if sys.platform == "darwin" else "linux")


def run(files, out_dir=None):
    pictures, problems = [], []
    destinations = set()
    for f in files:
        if not os.path.isfile(f):
            problems.append(f"{f} does not exist.")
            continue
        folder = out_dir or os.path.join(os.path.dirname(os.path.abspath(f)), "check")
        os.makedirs(folder, exist_ok=True)
        stem = os.path.splitext(os.path.basename(f))[0]
        original_stem, suffix = stem, 2
        key = lambda name: (os.path.normcase(os.path.abspath(folder)), os.path.normcase(name))
        while key(stem) in destinations:
            stem = f"{original_stem}-{suffix}"
            suffix += 1
        destinations.add(key(stem))
        try:
            if f.lower().endswith(".pptx"):
                got, why = pptx_pictures(f, folder, stem)
            elif f.lower().endswith(".html"):
                got, why = html_pictures(f, folder, stem)
            else:
                got, why = [], f"{f} is not a .pptx or .html file."
        except (OSError, subprocess.SubprocessError) as e:
            got, why = [], f"{f}: the check failed ({type(e).__name__}); no fresh pictures were verified."
        pictures += got
        if why:
            problems.append(why)
    if pictures:
        print("Look at every one of these pictures before handing over:")
        for p in pictures:
            print("  " + p)
        print("Look for: text cut off or running into other text, text over a shape, Arabic letters broken apart,")
        print("an empty slide, and anything that does not match the chosen design.")
    for p in problems:
        print("Not checked: " + p)
    return 0 if pictures and not problems else 1


def html_pictures(path, folder, stem):
    browser = find_browser()
    if not browser:
        return [], (f"{os.path.basename(path)}: no Chrome, Edge or Chromium was found, so no pictures were taken. "
                    "Open the file in a browser and look at it yourself, or set DECKCRAFT_CHROME.")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    url = Path(path).resolve().as_uri()
    shots = []
    profile = tempfile.mkdtemp(prefix="deckcraft-chrome-")
    try:
        with BrowserSession(browser, profile) as session:
            if 'class="slide"' in text:
                n = text.count('<section class="slide"')
                for i in range(1, n + 1):
                    out = os.path.join(profile, f"{stem}-{i:02d}.png")
                    session.shoot(f"{url}#{i}", out, 1600, 900)
                    shots.append(out)
            else:
                out = os.path.join(profile, f"{stem}-desktop.png")
                phone = os.path.join(profile, f"{stem}-phone.png")
                session.shoot(url, out, 1280, 900, full_page=True)
                session.shoot(url, phone, 390, 900, full_page=True)
                shots += [out, phone]
        if not shots or any(not os.path.isfile(s) for s in shots):
            return [], f"the browser did not save every fresh picture of {path}."
        pictures = []
        for shot in shots:
            dest = os.path.join(folder, os.path.basename(shot))
            shutil.copy2(shot, dest)
            pictures.append(dest)
        return pictures, None
    except (OSError, subprocess.SubprocessError) as e:
        return [], f"{os.path.basename(path)}: browser check failed ({type(e).__name__}); no fresh pictures were verified."
    finally:
        shutil.rmtree(profile, ignore_errors=True)


def _run_tool(cmd, timeout):
    # Renderers spawn helpers. Give this run its own group so a timeout cannot leave
    # its children alive or affect another Chrome/Office session on a shared machine.
    options = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt" else {"start_new_session": True}
    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
    try:
        status = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            else:
                os.killpg(process.pid, signal.SIGKILL)
        except (OSError, subprocess.SubprocessError):
            if process.poll() is None:
                process.kill()
        finally:
            process.wait(timeout=10)
        raise
    if status:
        raise subprocess.CalledProcessError(status, cmd)


def _give_fonts(pptx_path, font_dir):
    """LibreOffice cannot read fonts embedded in a .pptx, so it gets the same bundled files."""
    import zipfile
    from . import fonts
    try:
        with zipfile.ZipFile(pptx_path) as package:
            xml = package.read("ppt/presentation.xml").decode("utf-8")
    except (KeyError, OSError, zipfile.BadZipFile):
        return
    names = set(re.findall(r'<p:font typeface="([^"]+)"', xml))
    os.makedirs(font_dir, exist_ok=True)
    for e in fonts.index():
        if e["typeface"] in names:
            shutil.copy(os.path.join(fonts.FONTS_DIR, e["file"]), font_dir)


def pptx_pictures(path, folder, stem):
    office = find_office()
    if not office:
        return [], (f"{os.path.basename(path)}: LibreOffice was not found, so no pictures were taken. "
                    "Open the file in PowerPoint or Keynote and look at every slide yourself.")
    profile = tempfile.mkdtemp(prefix="deckcraft-office-")
    try:
        _give_fonts(path, os.path.join(profile, "user", "fonts"))
        render_dir = os.path.join(profile, "render")
        os.makedirs(render_dir)
        cmd = [office, f"-env:UserInstallation={Path(profile).resolve().as_uri()}", "--headless",
               "--convert-to", "pdf", "--outdir", render_dir, os.path.abspath(path)]
        _run_tool(cmd, 240)
        # LibreOffice names the PDF after its input, not a caller-supplied output stem.
        pdf = os.path.join(render_dir, os.path.splitext(os.path.basename(path))[0] + ".pdf")
        if not os.path.isfile(pdf):
            return [], f"LibreOffice could not open {os.path.basename(path)}. Open it in PowerPoint to see why."
        tool = shutil.which("pdftoppm")
        if tool:
            _run_tool([tool, "-r", "80", "-png", pdf, os.path.join(render_dir, stem)], 240)
            shots = sorted(glob.glob(os.path.join(glob.escape(render_dir), glob.escape(stem) + "-*.png")))
            if not shots:
                return [], f"No fresh slide pictures were saved for {path}."
        else:
            shots = [pdf]
        pictures = []
        for shot in shots:
            dest = os.path.join(folder, stem + ".pdf" if shot == pdf else os.path.basename(shot))
            shutil.copy2(shot, dest)
            pictures.append(dest)
        return pictures, None
    except (OSError, subprocess.SubprocessError) as e:
        return [], f"{os.path.basename(path)}: PowerPoint check failed ({type(e).__name__}); no fresh pictures were verified."
    finally:
        shutil.rmtree(profile, ignore_errors=True)
