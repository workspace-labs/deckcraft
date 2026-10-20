"""Load and check a deckcraft content file (the words of one deck, in JSON).

The rules live in references/content-format.md. Every problem becomes one plain
numbered sentence, so the agent can fix exactly that and run again.
"""
import json
import re

LANGS = ("en", "ar")

# For each slide type: required fields, optional fields.
SLIDE_TYPES = {
    "title": ({"title"}, {"eyebrow", "subtitle", "note"}),
    "section": ({"title"}, {"eyebrow", "subtitle"}),
    "points": ({"title", "points"}, {"eyebrow"}),
    "numbers": ({"title", "items"}, {"eyebrow"}),
    "chart": ({"title", "bars"}, {"eyebrow", "note"}),
    "quote": ({"text"}, {"by"}),
    "closing": ({"title"}, {"subtitle", "contact"}),
}

# Longest text each field may hold, in characters.
LIMITS = {
    "title": 90, "eyebrow": 40, "subtitle": 160, "note": 80, "text": 260,
    "by": 60, "contact": 80, "point": 140, "value": 20, "label": 40,
}

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ContentError(Exception):
    """The content file has problems; .problems lists them in plain words."""

    def __init__(self, problems):
        self.problems = problems
        super().__init__("\n".join(f"  {i}. {p}" for i, p in enumerate(problems, 1)))


def load(path):
    """Read a content file from disk and check it. Returns the content dict."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ContentError([f"The file is not valid JSON (line {e.lineno}, column {e.colno}): {e.msg}."])
    except OSError as e:
        raise ContentError([f"The file cannot be read: {e.strerror}."])
    return check(data)


def check(data):
    """Check a content dict. Returns it with defaults filled in, or raises ContentError."""
    problems = []
    if not isinstance(data, dict):
        raise ContentError(["The file must hold one JSON object with \"lang\", \"title\" and \"slides\"."])

    _unknown(data, {"lang", "title", "org", "brand", "slides"}, "The file", problems)
    lang = data.get("lang", "en")
    if lang not in LANGS:
        problems.append(f"\"lang\" must be \"en\" or \"ar\", not {json.dumps(lang)}.")
    _text(data, "title", "The file", problems, required=True)
    _text(data, "org", "The file", problems, limit=40)

    brand = data.get("brand")
    if brand is not None:
        if not isinstance(brand, dict):
            problems.append("\"brand\" must be an object like {\"accent\": \"#0055AA\", \"logo\": \"logo.png\"}.")
        else:
            _unknown(brand, {"accent", "logo"}, "\"brand\"", problems)
            if "accent" in brand and not (isinstance(brand["accent"], str) and HEX.match(brand["accent"])):
                problems.append("\"brand.accent\" must be a colour like \"#0055AA\".")
            if "logo" in brand and not (isinstance(brand["logo"], str) and brand["logo"].lower().endswith((".png", ".jpg", ".jpeg"))):
                problems.append("\"brand.logo\" must be the path of a .png or .jpg file.")

    slides = data.get("slides")
    if not isinstance(slides, list) or not slides:
        problems.append("\"slides\" must be a list with at least one slide.")
        slides = []
    elif len(slides) > 40:
        problems.append(f"There are {len(slides)} slides; deckcraft makes up to 40. Split the deck.")

    for n, s in enumerate(slides, 1):
        _slide(s, n, problems)

    if problems:
        raise ContentError(problems)
    out = dict(data)
    out["lang"] = lang
    out.setdefault("org", "")
    return out


def _slide(s, n, problems):
    where = f"Slide {n}"
    if not isinstance(s, dict) or "type" not in s:
        problems.append(f"{where} must be an object with a \"type\" ({', '.join(SLIDE_TYPES)}).")
        return
    kind = s["type"]
    if kind not in SLIDE_TYPES:
        problems.append(f"{where}: \"{kind}\" is not a slide type. Use one of: {', '.join(SLIDE_TYPES)}.")
        return
    where = f"Slide {n} ({kind})"
    need, may = SLIDE_TYPES[kind]
    _unknown(s, need | may | {"type"}, where, problems)
    for field in need | may:
        if field in ("points", "items", "bars"):
            continue
        _text(s, field, where, problems, required=field in need)

    if kind == "points":
        pts = s.get("points")
        if not isinstance(pts, list) or not 2 <= len(pts) <= 6:
            problems.append(f"{where}: \"points\" must be a list of 2 to 6 short sentences.")
        else:
            for i, p in enumerate(pts, 1):
                if not isinstance(p, str) or not p.strip():
                    problems.append(f"{where}: point {i} must be text.")
                elif len(p) > LIMITS["point"]:
                    problems.append(f"{where}: point {i} is {len(p)} characters; keep it under {LIMITS['point']}.")
    elif kind == "numbers":
        items = s.get("items")
        if not isinstance(items, list) or not 2 <= len(items) <= 4:
            problems.append(f"{where}: \"items\" must be a list of 2 to 4 numbers, each {{\"value\": \"96%\", \"label\": \"On time\"}}.")
        else:
            for i, it in enumerate(items, 1):
                _pair(it, ("value", "label"), f"{where}: number {i}", problems)
    elif kind == "chart":
        bars = s.get("bars")
        if not isinstance(bars, list) or not 2 <= len(bars) <= 8:
            problems.append(f"{where}: \"bars\" must be a list of 2 to 8 bars, each {{\"label\": \"Q1\", \"value\": 39.1}}.")
        else:
            for i, b in enumerate(bars, 1):
                w = f"{where}: bar {i}"
                if not isinstance(b, dict):
                    problems.append(f"{w} must be an object.")
                    continue
                _unknown(b, {"label", "value", "show"}, w, problems)
                _text(b, "label", w, problems, required=True, limit=LIMITS["label"])
                _text(b, "show", w, problems, limit=LIMITS["value"])
                v = b.get("value")
                if isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0:
                    problems.append(f"{w}: \"value\" must be a number of 0 or more.")


def _pair(it, fields, where, problems):
    if not isinstance(it, dict):
        problems.append(f"{where} must be an object.")
        return
    _unknown(it, set(fields), where, problems)
    for f in fields:
        _text(it, f, where, problems, required=True)


def _text(obj, field, where, problems, required=False, limit=None):
    if field not in obj:
        if required:
            problems.append(f"{where} needs \"{field}\".")
        return
    v = obj[field]
    if not isinstance(v, str) or (required and not v.strip()):
        problems.append(f"{where}: \"{field}\" must be text.")
        return
    limit = limit or LIMITS.get(field)
    if limit and len(v) > limit:
        problems.append(f"{where}: \"{field}\" is {len(v)} characters; keep it under {limit}.")


def _unknown(obj, allowed, where, problems):
    for k in obj:
        if k not in allowed:
            problems.append(f"{where}: \"{k}\" is not a known field. Known: {', '.join(sorted(allowed))}.")
