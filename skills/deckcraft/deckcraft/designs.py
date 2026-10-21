"""The 12-design library: find, load and complete a design.

Each design is a folder in designs/ holding design.json (colours, fonts and the
slide look) and style.css (the web page look). A design.json only lists what
differs from DEFAULTS below; load() fills in the rest.
"""
import copy
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGNS_DIR = os.path.join(os.path.dirname(HERE), "designs")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Sizes are in slide units: 1 unit = 1% of the slide width (a slide is 100 x 56.25).
DEFAULTS = {
    "deco": [],
    "area": [7, 6, 86, 44.25],          # x, y, width, height where text may go
    "align": "start",                   # start (left in English) or center
    "title": {"font": "display", "size": 5.4, "color": "ink", "case": "none", "italic": False,
              "tracking": 0, "leading": 1.05, "w": 0.85, "pos": "middle"},
    "eyebrow": {"style": "text", "font": "body", "size": 1.5, "color": "accent", "fill": None, "alpha": 1,
                "line": None, "line_alpha": 1, "case": "upper", "tracking": 0.12, "weight": 600,
                "italic": False, "rotate": 0, "indent": 0, "mark": None, "mark_color": "accent"},
    "body": {"font": "body", "size": 2.0, "color": "ink", "leading": 1.4},
    "marker": {"style": "dot", "color": "accent"},
    "cards": {"style": "none", "fill": "surface", "alpha": 1, "line": None, "line_alpha": 1, "line_w": 0.15,
              "radius": 0, "shadow": False, "pad": 1.6, "divider": "line", "divider_alpha": 1,
              "fills": [], "inks": [], "rotate": []},
    "numbers": "row",                   # row, row-auto, column-right or table
    "value": {"font": "display", "size": 3.6, "color": "ink", "first": None},
    "label": {"font": "body", "size": 1.4, "color": "muted", "italic": False, "case": "none", "tracking": 0},
    "org": {"pos": "bottom-left", "font": "body", "size": 1.2, "color": "muted", "case": "none",
            "tracking": 0, "weight": 400},
    "bars": {"fill": "line", "last": "accent", "radius": 0.4, "base": None, "line": None},
}
FONT_ROLES = ("display", "body", "display_ar", "body_ar")
REQUIRED_COLORS = ("bg", "ink", "muted", "accent", "surface", "line")


class DesignError(Exception):
    pass


def folders():
    """All design folders, in library order."""
    return sorted(d for d in os.listdir(DESIGNS_DIR)
                  if os.path.isfile(os.path.join(DESIGNS_DIR, d, "design.json")))


def find(key):
    """Find a design folder by number ("3", "03"), slug ("nature-earth") or name."""
    k = str(key).strip().lower()
    for d in folders():
        num, slug = d.split("-", 1)
        if k in (num, num.lstrip("0"), slug, d) or k == _name(d).lower():
            return d
    names = ", ".join(f"{d[:2]} {_name(d)}" for d in folders())
    raise DesignError(f"There is no design \"{key}\". The designs are: {names}.")


def _name(folder):
    with open(os.path.join(DESIGNS_DIR, folder, "design.json"), encoding="utf-8") as f:
        return json.load(f)["name"]


def load(key, brand=None):
    """Load a design, fill in the defaults and apply a brand accent if given."""
    folder = find(key)
    path = os.path.join(DESIGNS_DIR, folder)
    with open(os.path.join(path, "design.json"), encoding="utf-8") as f:
        d = json.load(f)
    problems = check(d)
    if problems:
        raise DesignError(f"Design {folder} is broken: " + " ".join(problems))
    slide = copy.deepcopy(DEFAULTS)
    for k, v in d.get("slide", {}).items():
        if isinstance(v, dict) and isinstance(slide.get(k), dict):
            slide[k].update(v)
        else:
            slide[k] = v
    d["slide"] = slide
    d["folder"] = path
    css = os.path.join(path, "style.css")
    d["css"] = ""
    if os.path.isfile(css):
        with open(css, encoding="utf-8") as f:
            d["css"] = f.read()
    if brand and brand.get("accent"):
        d["colors"]["accent"] = brand["accent"]
    return d


def check(d):
    """Problems with a raw design.json, as sentences (empty when fine)."""
    problems = []
    for k in ("id", "slug", "name", "good_for", "colors", "fonts"):
        if k not in d:
            problems.append(f"It needs \"{k}\".")
    colors = d.get("colors", {})
    for k in REQUIRED_COLORS:
        if k not in colors:
            problems.append(f"Colour \"{k}\" is missing.")
    for k, v in colors.items():
        if not (isinstance(v, str) and HEX.match(v)):
            problems.append(f"Colour \"{k}\" must be like #12AB34.")
    fonts = d.get("fonts", {})
    for role in FONT_ROLES:
        f = fonts.get(role)
        if not isinstance(f, dict) or not all(k in f for k in ("family", "weight", "width", "fallback")):
            problems.append(f"Font \"{role}\" needs family, weight, width and fallback.")
    for k in d.get("slide", {}):
        if k not in DEFAULTS:
            problems.append(f"\"slide.{k}\" is not a known setting.")
    return problems


def color(design, value):
    """A colour by name ("accent") or as hex; None stays None."""
    if value is None:
        return None
    if isinstance(value, str) and value.startswith("#"):
        return value.upper()
    try:
        return design["colors"][value].upper()
    except KeyError:
        raise DesignError(f"Design {design['id']} uses an unknown colour \"{value}\".")


def font(design, role, lang):
    """The font entry for a role ("display" or "body") in a language."""
    fonts = design["fonts"]
    return fonts[role + "_ar"] if lang == "ar" else fonts[role]


# The weights each library font really has on Google Fonts. Asking for any other
# weight makes Google refuse the whole stylesheet, so every request goes through here.
AVAILABLE = {
    "Alexandria": range(100, 1000, 100), "Almarai": (300, 400, 700, 800), "Amiri": (400, 700),
    "Anton": (400,), "Baloo Bhaijaan 2": range(400, 900, 100), "Barlow": range(100, 1000, 100),
    "Barlow Condensed": range(100, 1000, 100), "Bricolage Grotesque": range(200, 900, 100),
    "Cairo": range(200, 1100, 100), "Cormorant Garamond": range(300, 800, 100),
    "Crimson Pro": range(200, 1000, 100), "El Messiri": range(400, 800, 100),
    "Inter Tight": range(100, 1000, 100), "Lalezar": (400,), "Lato": (100, 300, 400, 700, 900),
    "Manrope": range(200, 900, 100), "Noto Kufi Arabic": range(100, 1000, 100),
    "Noto Naskh Arabic": range(400, 800, 100), "Noto Sans Arabic": range(100, 1000, 100),
    "Nunito": range(200, 1100, 100), "Outfit": range(100, 1000, 100), "Reem Kufi": range(400, 800, 100),
    "Rubik": range(300, 1000, 100), "Sora": range(100, 900, 100), "Source Sans 3": range(200, 1000, 100),
    "Source Serif 4": range(200, 1000, 100), "Young Serif": (400,),
}


def weight(family, wanted):
    """The nearest weight the family really has."""
    have = AVAILABLE.get(family, (400, 700))
    return min(have, key=lambda w: (abs(w - wanted), w))


def google_fonts_url(design):
    """One Google Fonts stylesheet link for every font the design uses."""
    want = {}

    def add(f, wanted=None, italic=False):
        fam = f["family"]
        want.setdefault(fam, set()).add((int(italic), weight(fam, wanted or f["weight"])))

    for role in FONT_ROLES:
        f = design["fonts"][role]
        for w in (400, f["weight"], 700):
            add(f, w)
    slide = design.get("slide", {})
    for lang in ("en", "ar"):
        for role in ("title", "eyebrow", "body", "value", "label", "org"):
            st = dict(DEFAULTS[role], **slide.get(role, {}))
            f = font(design, st["font"], lang)
            add(f, st.get("weight"), bool(st.get("italic")) and lang == "en")
        # The page's navigation contact uses body weight 600.
        add(font(design, "body", lang), 600)
        if slide.get("org", {}).get("pos") == "footnote" and lang == "en":
            # Slide footnotes use display italic; the page footer uses body italic.
            add(font(design, "display", lang), 400, True)
            add(font(design, "body", lang), italic=True)
    parts = []
    for fam in sorted(want):
        axes = sorted(want[fam])
        if any(i for i, _ in axes):
            spec = "ital,wght@" + ";".join(f"{i},{w}" for i, w in axes)
        else:
            spec = "wght@" + ";".join(str(w) for _, w in axes)
        parts.append("family=" + fam.replace(" ", "+") + ":" + spec)
    return "https://fonts.googleapis.com/css2?" + "&".join(parts) + "&display=swap"
