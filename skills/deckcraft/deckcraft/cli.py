"""deckcraft command line: list the designs, make files, take check pictures."""
import argparse
import os
import sys

from . import content as content_mod
from . import designs
from .layout import layout_deck

FORMATS = ("pptx", "slides", "page")
OUTPUT_NAMES = {"pptx": "{name}.pptx", "slides": "{name}-slides.html", "page": "{name}-page.html"}


def main(argv=None):
    p = argparse.ArgumentParser(prog="deckcraft", description="Decks and web pages in 12 approved designs.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("designs", help="list the 12 designs")
    sub.add_parser("picker", help="print the path of the design picker page")

    m = sub.add_parser("make", help="make files from a content file")
    m.add_argument("content", help="the content .json file")
    m.add_argument("--design", required=True, help="design number, like 3 or 03")
    m.add_argument("--formats", default="pptx,slides,page", help="any of pptx, slides, page (comma separated)")
    m.add_argument("--out", default="out", help="folder for the made files")
    m.add_argument("--name", help="file name without extension (default: from the content file)")
    m.add_argument("--fonts", choices=("design", "safe"), default="design",
                   help="PowerPoint fonts: the design's fonts, or plain fonts every computer has")

    c = sub.add_parser("check", help="take a picture of every slide and page that was made")
    c.add_argument("files", nargs="+", help="made .pptx and .html files")
    c.add_argument("--out", default=None, help="folder for the pictures (default: <file folder>/check)")

    x = sub.add_parser("extract", help="read an existing .pptx or .html into a draft content file")
    x.add_argument("file", help="their .pptx or .html")
    x.add_argument("--out", required=True, help="the draft content .json to write")

    w = sub.add_parser("same-words", help="list words of the original that the content file lost")
    w.add_argument("original", help="their .pptx or .html")
    w.add_argument("content", help="the content .json")

    a = p.parse_args(argv)
    try:
        if a.cmd == "designs":
            return list_designs()
        if a.cmd == "picker":
            print(os.path.join(designs.DESIGNS_DIR, "picker.html"))
            return 0
        if a.cmd == "make":
            return make(a)
        if a.cmd == "extract":
            return extract_cmd(a)
        if a.cmd == "same-words":
            return same_words_cmd(a)
        if a.cmd == "check":
            from . import check
            return check.run(a.files, a.out)
    except content_mod.ContentError as e:
        print("Nothing made yet. Change these in the content file, then run again:", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1
    except designs.DesignError as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


def list_designs():
    for folder in designs.folders():
        d = designs.load(folder)
        print(f"{d['id']}  {d['name']:<18} {d['good_for']}")
    return 0


def make(a):
    content = content_mod.load(a.content)
    formats = [f.strip() for f in a.formats.split(",") if f.strip()]
    bad = [f for f in formats if f not in FORMATS]
    if bad or not formats:
        print(f"Unknown format {', '.join(bad) or '(none)'}. Use any of: {', '.join(FORMATS)}.", file=sys.stderr)
        return 1
    design = designs.load(a.design, content.get("brand"))
    base_dir = os.path.dirname(os.path.abspath(a.content))
    name = a.name or os.path.splitext(os.path.basename(a.content))[0]
    os.makedirs(a.out, exist_ok=True)
    slides, warnings = layout_deck(content, design, base_dir)
    made = []
    for f in formats:
        path = os.path.join(a.out, OUTPUT_NAMES[f].format(name=name))
        if f == "slides":
            from . import html_slides
            _write(path, html_slides.render(slides, design, content))
        elif f == "page":
            from . import html_page
            page, page_warnings = html_page.render(content, design, base_dir)
            warnings += page_warnings
            _write(path, page)
        else:
            from . import pptx
            warnings += pptx.write(path, slides, design, content, fonts=a.fonts)
        made.append(path)
    print(f"Made with design {design['id']} {design['name']}:")
    for path in made:
        print("  " + path)
    if warnings:
        print("Look at these before handing over:")
        for i, w in enumerate(dict.fromkeys(warnings), 1):
            print(f"  {i}. {w}")
    print("Next: take the check pictures with  deckcraft check " + " ".join(made))
    return 0


def extract_cmd(a):
    import json
    from . import extract
    try:
        data, report = extract.draft(a.file)
    except (ValueError, OSError, KeyError) as e:
        print(f"Cannot read {a.file}: {e}", file=sys.stderr)
        return 1
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Draft written: {a.out} ({len(data['slides'])} slides, lang {data['lang']}).")
    print("Every word was copied as it is. Change slide types if a better one fits (numbers, chart, quote),")
    print("but never the words. Add \"org\" if you know it. Then run same-words before making.")
    for i, r in enumerate(report, 1):
        print(f"  {i}. {r}")
    return 0


def same_words_cmd(a):
    from . import extract
    data = content_mod.load(a.content)
    missing = extract.same_words(a.original, data)
    if not missing:
        print("Every word of the original is in the content file.")
        return 0
    print("These words of the original are missing from the content file. Put them back, or tell the person why:")
    for word, n in sorted(missing.items()):
        print(f"  {word}" + (f" (x{n})" if n > 1 else ""))
    return 1


def _write(path, text):
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
