"""The bundled font files (fonts/index.json, made by tools/fetch_fonts.py).

Each static TTF has its own name inside: Manrope at 800 is the font "Manrope ExtraBold"
(style Regular), Manrope at 700 is "Manrope" (style Bold). A PowerPoint text names the
exact font and sets bold/italic from its style, so it finds the embedded file.
"""
import json
import os

from .designs import DESIGNS_DIR

FONTS_DIR = os.path.join(os.path.dirname(DESIGNS_DIR), "fonts")
_index = None


def index():
    global _index
    if _index is None:
        path = os.path.join(FONTS_DIR, "index.json")
        try:
            with open(path, encoding="utf-8") as f:
                _index = json.load(f)
        except OSError:
            _index = []
    return _index


def lookup(family, weight, italic=False):
    """The bundled file for a family at a weight (nearest weight, same slant), or None."""
    same = [e for e in index() if e["family"] == family and e["italic"] == bool(italic)]
    if not same:
        return None
    best = min(same, key=lambda e: (abs(e["weight"] - weight), e["weight"]))
    return dict(best, path=os.path.join(FONTS_DIR, best["file"]),
                bold="Bold" in best["style"], slanted="Italic" in best["style"])
