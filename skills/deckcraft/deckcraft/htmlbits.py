"""Small pieces shared by the HTML slides and the web page writers."""
import base64
import html

from .images import mime

STAR6 = "50% 0,61% 32%,95% 25%,70% 50%,95% 75%,61% 68%,50% 100%,39% 68%,5% 75%,30% 50%,5% 25%,39% 32%"


def esc(text):
    return html.escape(text, quote=True)


def rgba(hex_color, alpha=1.0):
    if hex_color is None:
        return "transparent"
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgb({r} {g} {b})" if alpha >= 1 else f"rgb({r} {g} {b} / {alpha:g})"


def font_stack(family, fallback):
    generic = "serif" if fallback in ("Georgia", "Times New Roman", "Garamond") else "sans-serif"
    return f"'{family}', '{fallback}', {generic}"


def data_uri(path):
    with open(path, "rb") as f:
        return f"data:{mime(path)};base64," + base64.b64encode(f.read()).decode("ascii")


def pattern_svg(line_hex, alpha):
    """The Gulf Heritage tile: two squares (one turned 45 degrees) and a ring, as a data URI."""
    c = line_hex.replace("#", "%23")
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='40' height='40' viewBox='0 0 40 40'>"
           f"<g fill='none' stroke='{c}' stroke-opacity='{alpha:g}'>"
           "<rect x='10' y='10' width='20' height='20'/>"
           "<rect x='10' y='10' width='20' height='20' transform='rotate(45 20 20)'/>"
           "<circle cx='20' cy='20' r='4'/></g></svg>")
    return "data:image/svg+xml," + svg.replace("<", "%3C").replace(">", "%3E").replace("'", "%27")


def head(title, lang, fonts_url, css):
    direction = "rtl" if lang == "ar" else "ltr"
    return (f"<!doctype html>\n<html lang=\"{lang}\" dir=\"{direction}\">\n<head>\n<meta charset=\"utf-8\">\n"
            f"<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n<title>{esc(title)}</title>\n"
            "<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n"
            "<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n"
            f"<link rel=\"stylesheet\" href=\"{esc(fonts_url)}\">\n<style>\n{css}\n</style>\n</head>\n")
