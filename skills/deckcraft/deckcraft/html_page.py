"""Write the web page: one scrolling page from the same content as the slides.

Each slide becomes a section: title -> hero, numbers -> a band of numbers, points ->
a list, chart -> bars, quote -> a quote, section -> a break, closing -> contact.
The shared layout is designs/page-base.css; the design's style.css adds its look.
"""
import os
import re

from . import designs
from .htmlbits import data_uri, esc, font_stack, head

BASE_CSS = os.path.join(designs.DESIGNS_DIR, "page-base.css")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def render(content, design, base_dir="."):
    """Returns (html, warnings)."""
    lang = content["lang"]
    s = design["slide"]
    warnings = []
    with open(BASE_CSS, encoding="utf-8") as f:
        css = f.read() + "\n" + variables(design, lang) + "\n" + design["css"]
    classes = [f"eyebrow-{s['eyebrow']['style']}", f"cards-{_cards_class(s)}", f"marker-{s['marker']['style']}",
               f"align-{s['align']}"]
    out = [head(content["title"], lang, designs.google_fonts_url(design), css)]
    out.append(f"<body class=\"{' '.join(classes)}\">\n")
    out.append(nav(content, base_dir, warnings))
    out.append("<main>\n")
    for i, slide in enumerate(content["slides"]):
        out.append(SECTIONS[slide["type"]](slide, i == 0, lang))
    out.append("</main>\n")
    org = content.get("org") or ""
    out.append(f"<footer><div class=\"wrap\">{esc(org)}</div></footer>\n</body>\n</html>\n")
    return "".join(out), warnings


def _cards_class(s):
    if s["numbers"] == "table":
        return "table"
    return s["cards"]["style"]


def variables(design, lang):
    s = design["slide"]
    c = lambda k: designs.color(design, k)  # noqa: E731
    disp, body = designs.font(design, "display", lang), designs.font(design, "body", lang)
    t, eb, cards, bars, val = s["title"], s["eyebrow"], s["cards"], s["bars"], s["value"]
    v = {
        "--display": font_stack(disp["family"], disp["fallback"]),
        "--display-w": designs.weight(disp["family"], disp["weight"]),
        "--body": font_stack(body["family"], body["fallback"]),
        "--body-w": designs.weight(body["family"], body["weight"]),
        "--title": c(t["color"]),
        "--title-case": "uppercase" if t["case"] == "upper" else "none",
        "--title-track": f"{t['tracking']:g}em",
        "--title-style": "italic" if t["italic"] else "normal",
        "--title-lead": f"{max(t['leading'], 1.02):g}",
        "--eyebrow": c(eb["color"]),
        "--eyebrow-bg": c(eb["fill"]) or "transparent",
        "--eyebrow-line": c(eb["line"]) or "transparent",
        "--eyebrow-case": "uppercase" if eb["case"] == "upper" else "none",
        "--eyebrow-track": f"{eb['tracking']:g}em",
        "--value": c(val["color"]),
        "--value-first": c(val["first"] or val["color"]),
        "--card-line": c(cards["line"] or "line"),
        "--card-r": f"{max(cards['radius'], 0) * 8:g}px",
        "--marker": c(s["marker"]["color"]),
        "--bar": c(bars["fill"]),
        "--bar-last": c(bars["last"]),
        "--bar-base": c(bars["base"]) or "transparent",
        "--bar-r": f"{bars['radius'] * 8:g}px",
        "--bar-line": f"2px solid {c(bars['line'])}" if bars["line"] else "0",
        "--quote-mark": "'\\201C'" if lang == "en" else "'\\201D'",
    }
    for k, val_hex in design["colors"].items():
        v["--" + k if k in ("bg", "ink", "muted", "accent", "surface", "line") else "--c-" + k] = val_hex
    return ":root{" + ";".join(f"{k}:{val}" for k, val in v.items()) + "}"


def nav(content, base_dir, warnings):
    org = esc(content.get("org") or content["title"])
    logo = ""
    path = (content.get("brand") or {}).get("logo")
    if path:
        full = path if os.path.isabs(path) else os.path.join(base_dir, path)
        try:
            logo = f"<img class=\"logo\" src=\"{data_uri(full)}\" alt=\"{org}\">"
        except OSError as e:
            warnings.append(f"The logo cannot be used: {e.strerror}.")
    contact = next((s.get("contact") for s in content["slides"] if s["type"] == "closing" and s.get("contact")), None)
    link = f"<a href=\"#contact\">{esc(contact)}</a>" if contact else ""
    name = "" if logo else f"<span class=\"org\">{org}</span>"
    if logo:
        logo = logo.replace("class=\"logo\"", "class=\"logo org\"")
    return f"<header class=\"nav\"><div class=\"wrap\">{logo}{name}{link}</div></header>\n"


def _h(text, first):
    tag = "h1" if first else "h2"
    return f"<{tag}>{esc(text)}</{tag}>"


def _eyebrow(s):
    return f"<p class=\"eyebrow\">{esc(s['eyebrow'])}</p>" if s.get("eyebrow") else ""


def _section(cls, inner, extra=""):
    return f"<section class=\"block {cls}\"{extra}><div class=\"wrap\">{inner}</div></section>\n"


def title(s, first, lang):
    inner = _eyebrow(s) + _h(s["title"], first)
    if s.get("subtitle"):
        inner += f"<p class=\"lead\">{esc(s['subtitle'])}</p>"
    if s.get("note"):
        inner += f"<p class=\"note\">{esc(s['note'])}</p>"
    return _section("hero", inner)


def section(s, first, lang):
    inner = _eyebrow(s) + _h(s["title"], first)
    if s.get("subtitle"):
        inner += f"<p class=\"lead\">{esc(s['subtitle'])}</p>"
    return _section("section-break", inner)


def numbers(s, first, lang):
    items = "".join(f"<li><b>{esc(i['value'])}</b><span>{esc(i['label'])}</span></li>" for i in s["items"])
    return _section("numbers", _eyebrow(s) + _h(s["title"], first) + f"<ul class=\"cards\">{items}</ul>")


def points(s, first, lang):
    items = "".join(f"<li>{esc(p)}</li>" for p in s["points"])
    return _section("points-block", _eyebrow(s) + _h(s["title"], first) + f"<ul class=\"points\">{items}</ul>")


def chart(s, first, lang):
    biggest = max(b["value"] for b in s["bars"]) or 1
    bars, words = [], []
    for i, b in enumerate(s["bars"]):
        shown = b.get("show") or (str(int(b["value"])) if float(b["value"]).is_integer() else f"{b['value']:.1f}")
        last = " last" if i == len(s["bars"]) - 1 else ""
        pct = max(1.5, 100 * b["value"] / biggest)
        bars.append(f"<div class=\"bar{last}\" style=\"--v:{pct:.1f}%\"><em>{esc(shown)}</em><span>{esc(b['label'])}</span></div>")
        words.append(f"{b['label']}: {shown}")
    inner = (_eyebrow(s) + _h(s["title"], first) +
             f"<div class=\"chart\" role=\"img\" aria-label=\"{esc('; '.join(words))}\">{''.join(bars)}</div>")
    if s.get("note"):
        inner += f"<p class=\"chart-note\">{esc(s['note'])}</p>"
    return _section("chart-block", inner)


def quote(s, first, lang):
    inner = f"<blockquote>{esc(s['text'])}</blockquote>"
    if s.get("by"):
        inner += f"<p class=\"by\">— {esc(s['by'])}</p>"
    if first:
        inner = f"<h1 class=\"visually-hidden\" style=\"position:absolute;clip:rect(0 0 0 0)\">{esc(s['text'][:60])}</h1>" + inner
    return _section("quote-block", inner)


def closing(s, first, lang):
    inner = _h(s["title"], first)
    if s.get("subtitle"):
        inner += f"<p class=\"lead\">{esc(s['subtitle'])}</p>"
    c = s.get("contact")
    if c:
        href = "mailto:" + c if EMAIL.match(c) else (c if c.startswith(("http://", "https://")) else "")
        inner += (f"<a class=\"contact\" href=\"{esc(href)}\">{esc(c)}</a>" if href
                  else f"<p class=\"contact\">{esc(c)}</p>")
    return _section("closing", inner, " id=\"contact\"")


SECTIONS = {"title": title, "section": section, "numbers": numbers, "points": points, "chart": chart,
            "quote": quote, "closing": closing}
