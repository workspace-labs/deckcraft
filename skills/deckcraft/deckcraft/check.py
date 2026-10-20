"""Take a picture of every slide and page that was made, for the agent to look at.

HTML slides and web pages: a Chrome-family browser in headless mode.
PowerPoint: LibreOffice turns it into a PDF, then pdftoppm (if present) into pictures.
Nothing is installed; a missing tool is reported in plain words.
"""
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

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
    for f in files:
        if not os.path.isfile(f):
            problems.append(f"{f} does not exist.")
            continue
        folder = out_dir or os.path.join(os.path.dirname(os.path.abspath(f)), "check")
        os.makedirs(folder, exist_ok=True)
        stem = os.path.splitext(os.path.basename(f))[0]
        if f.lower().endswith(".pptx"):
            got, why = pptx_pictures(f, folder, stem)
        elif f.lower().endswith(".html"):
            got, why = html_pictures(f, folder, stem)
        else:
            got, why = [], f"{f} is not a .pptx or .html file."
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
    url = "file://" + os.path.abspath(path).replace(os.sep, "/")
    if not url.startswith("file:///"):
        url = url.replace("file://", "file:///", 1)
    shots = []
    profile = tempfile.mkdtemp(prefix="deckcraft-chrome-")
    try:
        if 'class="slide"' in text:
            n = text.count('<section class="slide"')
            for i in range(1, n + 1):
                out = os.path.join(folder, f"{stem}-{i:02d}.png")
                _shoot(browser, profile, f"{url}#{i}", out, 1600, 900)
                shots.append(out)
        else:
            sections = len(re.findall(r'<section class="block', text))
            out = os.path.join(folder, f"{stem}-desktop.png")
            _shoot(browser, profile, url, out, 1280, 700 + 760 * sections)
            # Headless Chrome will not open a window under 500 px, so the phone view is a 390 px frame.
            phone = os.path.join(folder, f"{stem}-phone.png")
            frame = os.path.join(profile, "phone.html")
            h = 900 + 1100 * sections
            with open(frame, "w", encoding="utf-8") as fh:
                fh.write(f'<body style="margin:0;background:#888"><iframe src="{url}" width="390" height="{h}" '
                         'style="border:0;display:block"></iframe></body>')
            _shoot(browser, profile, "file:///" + frame.lstrip("/").replace(os.sep, "/"), phone, 500, h)
            shots += [out, phone]
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    missing = [s for s in shots if not os.path.isfile(s)]
    if missing:
        return [s for s in shots if s not in missing], f"the browser did not save {len(missing)} picture(s) of {path}."
    return shots, None


def _shoot(browser, profile, url, out, w, h):
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
           "--no-default-browser-check", f"--user-data-dir={profile}", f"--window-size={w},{h}",
           "--virtual-time-budget=8000", f"--screenshot={out}", url]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def _give_fonts(pptx_path, font_dir):
    """LibreOffice cannot read fonts embedded in a .pptx, so it gets the same bundled files."""
    import zipfile
    from . import fonts
    try:
        xml = zipfile.ZipFile(pptx_path).read("ppt/presentation.xml").decode("utf-8")
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
        cmd = [office, f"-env:UserInstallation=file:///{profile.lstrip('/').replace(os.sep, '/')}", "--headless",
               "--convert-to", "pdf", "--outdir", folder, path]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240)
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    pdf = os.path.join(folder, stem + ".pdf")
    if not os.path.isfile(pdf):
        return [], f"LibreOffice could not open {os.path.basename(path)}. Open it in PowerPoint to see why."
    tool = shutil.which("pdftoppm")
    if not tool:
        return [pdf], None
    subprocess.run([tool, "-r", "80", "-png", pdf, os.path.join(folder, stem)], timeout=240)
    pngs = sorted(glob.glob(os.path.join(folder, stem + "-*.png")))
    return (pngs or [pdf]), None
