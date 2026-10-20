"""Download every font weight the 12 designs use into skills/deckcraft/fonts/ (a maintainer tool).

Run it again after changing a design's fonts:  python3 tools/fetch_fonts.py
It lays out both examples with every design, collects each (family, weight, italic) a slide
really uses, downloads that static TTF from Google Fonts and the family's OFL licence, and
writes fonts/index.json. The skill itself never touches the network.
"""
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "deckcraft")
sys.path.insert(0, SKILL)

from deckcraft import content, designs  # noqa: E402
from deckcraft.layout import layout_deck  # noqa: E402
from deckcraft.pptx import fontfile  # noqa: E402

OUT = os.path.join(SKILL, "fonts")
UA = "Wget/1.21"  # Google Fonts answers a plain client with whole TTF files


def used():
    want = set()
    for lang in ("en", "ar"):
        c = content.load(os.path.join(SKILL, "examples", f"northwind-{lang}.json"))
        for f in designs.folders():
            slides, _ = layout_deck(c, designs.load(f))
            for s in slides:
                for e in s["elements"]:
                    if e["kind"] == "text":
                        want.add((e["family"], e["weight"], bool(e["italic"])))
    return sorted(want)


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main():
    os.makedirs(OUT, exist_ok=True)
    index = []
    families = {}
    for fam, w, ital in used():
        families.setdefault(fam, set()).add((int(ital), w))
    for fam, axes in sorted(families.items()):
        spec = "ital,wght@" + ";".join(f"{i},{w}" for i, w in sorted(axes))
        css = get("https://fonts.googleapis.com/css2?family=" + fam.replace(" ", "+") + ":" + spec).decode()
        for block in css.split("@font-face")[1:]:
            w = int(re.search(r"font-weight:\s*(\d+)", block).group(1))
            ital = "italic" in re.search(r"font-style:\s*(\w+)", block).group(1)
            url = re.search(r"url\((https://[^)]+\.ttf)\)", block).group(1)
            name = f"{fam.replace(' ', '')}-{w}{'i' if ital else ''}.ttf"
            data = get(url)
            info = fontfile.read(data)
            if info["fstype"] & 0x0002:
                raise SystemExit(f"{name} does not allow embedding (fsType {info['fstype']}).")
            with open(os.path.join(OUT, name), "wb") as f:
                f.write(data)
            index.append({"family": fam, "weight": w, "italic": ital, "file": name,
                          "typeface": info["family"], "style": info["style"]})
            print(f"{name:34} {info['family']} / {info['style']}  {len(data) // 1024} KB")
        lic = os.path.join(OUT, "licences", fam.replace(" ", "") + "-OFL.txt")
        if not os.path.exists(lic):
            os.makedirs(os.path.dirname(lic), exist_ok=True)
            folder = fam.lower().replace(" ", "")
            text = get(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{folder}/OFL.txt")
            with open(lic, "wb") as f:
                f.write(text)
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump(sorted(index, key=lambda x: (x["family"], x["weight"], x["italic"])), f, indent=1)
        f.write("\n")
    print(len(index), "font files")


if __name__ == "__main__":
    main()
