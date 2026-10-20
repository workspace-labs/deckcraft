"""Draw layout elements (layout.py) as DrawingML shapes on a slide."""
import math
import re
from xml.sax.saxutils import escape

from .parts import SLIDE_W

EMU = SLIDE_W / 100  # one slide unit (1% of the width) in EMU
PT = 9.6             # one slide unit in points (the slide is 960 pt wide)
BAD_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f]")
ARABIC = re.compile("[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]")


def emu(v):
    return int(round(v * EMU))


def clr(hex_color, alpha=1.0):
    a = "" if alpha >= 1 else f'<a:alpha val="{int(round(alpha * 100000))}"/>'
    return f'<a:srgbClr val="{hex_color[1:]}">{a}</a:srgbClr>'


def solid(hex_color, alpha=1.0):
    return f"<a:solidFill>{clr(hex_color, alpha)}</a:solidFill>" if hex_color else "<a:noFill/>"


def xfrm(e, flip=False):
    rot = f' rot="{int(round(e["rotate"] * 60000)) % 21600000}"' if e.get("rotate") else ""
    fl = ' flipH="1"' if flip else ""
    return (f'<a:xfrm{rot}{fl}><a:off x="{emu(e["x"])}" y="{emu(e["y"])}"/>'
            f'<a:ext cx="{max(1, emu(e["w"]))}" cy="{max(1, emu(e["h"]))}"/></a:xfrm>')


def shadow(sh):
    if not sh:
        return ""
    dist = emu(math.hypot(sh["dx"], sh["dy"]))
    ang = int(round(math.degrees(math.atan2(sh["dy"], sh["dx"])) * 60000)) % 21600000
    return (f'<a:effectLst><a:outerShdw blurRad="{emu(sh["blur"])}" dist="{dist}" dir="{ang}" algn="tl" '
            f'rotWithShape="0">{clr(sh["color"], sh["alpha"])}</a:outerShdw></a:effectLst>')


def geometry(e):
    """prstGeom or custGeom for an element, in its own EMU box."""
    kind = e["shape"]
    w, h = max(1, emu(e["w"])), max(1, emu(e["h"]))
    if kind in ("ellipse", "glow"):
        return '<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>'
    if kind == "diamond":
        return '<a:prstGeom prst="diamond"><a:avLst/></a:prstGeom>'
    if kind == "leaf":
        if e["corners"] == "tl-br":   # round top-left and bottom-right, points at top-right and bottom-left
            path = (f'<a:moveTo><a:pt x="{w}" y="0"/></a:moveTo>'
                    f'<a:arcTo wR="{w}" hR="{h}" stAng="16200000" swAng="-5400000"/>'
                    f'<a:arcTo wR="{w}" hR="{h}" stAng="5400000" swAng="-5400000"/>')
        else:                         # round top-right and bottom-left
            path = ('<a:moveTo><a:pt x="0" y="0"/></a:moveTo>'
                    f'<a:arcTo wR="{w}" hR="{h}" stAng="16200000" swAng="5400000"/>'
                    f'<a:arcTo wR="{w}" hR="{h}" stAng="5400000" swAng="5400000"/>')
        return _cust(w, h, path + "<a:close/>")
    if kind == "star6":
        pts = [(50, 0), (61, 32), (95, 25), (70, 50), (95, 75), (61, 68), (50, 100), (39, 68), (5, 75),
               (30, 50), (5, 25), (39, 32)]
        return _cust(w, h, _poly([(px * w / 100, py * h / 100) for px, py in pts]))
    if kind == "pattern":
        return _cust(w, h, _pattern(w, h, emu(e["tile"])), fill=False)
    radius = e.get("radius", 0)
    if radius:
        adj = int(min(50000, radius / max(0.01, min(e["w"], e["h"])) * 100000))
        if e.get("corners") == "top":
            return f'<a:prstGeom prst="round2SameRect"><a:avLst><a:gd name="adj1" fmla="val {adj}"/><a:gd name="adj2" fmla="val 0"/></a:avLst></a:prstGeom>'
        return f'<a:prstGeom prst="roundRect"><a:avLst><a:gd name="adj" fmla="val {adj}"/></a:avLst></a:prstGeom>'
    return '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'


def _cust(w, h, path, fill=True):
    nofill = "" if fill else ' fill="none"'
    return (f'<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/><a:rect l="0" t="0" r="r" b="b"/>'
            f'<a:pathLst><a:path w="{w}" h="{h}"{nofill}>{path}</a:path></a:pathLst></a:custGeom>')


def _poly(points):
    (x0, y0), rest = points[0], points[1:]
    s = f'<a:moveTo><a:pt x="{int(x0)}" y="{int(y0)}"/></a:moveTo>'
    s += "".join(f'<a:lnTo><a:pt x="{int(x)}" y="{int(y)}"/></a:lnTo>' for x, y in rest)
    return s + "<a:close/>"


def _pattern(w, h, tile):
    """The Gulf Heritage tile repeated: a square, the same square turned 45 degrees, and a ring."""
    out = []
    k = tile / 40.0
    cols, rows = int(math.ceil(w / tile)), int(math.ceil(h / tile))
    d = 14.142
    for j in range(rows):
        for i in range(cols):
            ox, oy = i * tile, j * tile

            def p(x, y):
                return (ox + x * k, oy + y * k)
            out.append(_poly([p(10, 10), p(30, 10), p(30, 30), p(10, 30)]))
            out.append(_poly([p(20, 20 - d), p(20 + d, 20), p(20, 20 + d), p(20 - d, 20)]))
            cx, cy = p(24, 20)
            r = int(4 * k)
            out.append(f'<a:moveTo><a:pt x="{int(cx)}" y="{int(cy)}"/></a:moveTo>'
                       f'<a:arcTo wR="{r}" hR="{r}" stAng="0" swAng="21600000"/><a:close/>')
    return "".join(out)


def fill_xml(e):
    if e["shape"] == "glow":
        c = e["fill"]
        return ('<a:gradFill rotWithShape="1"><a:gsLst>'
                f'<a:gs pos="0">{clr(c)}</a:gs><a:gs pos="100000">{clr(c, 0)}</a:gs></a:gsLst>'
                '<a:path path="circle"><a:fillToRect l="50000" t="50000" r="50000" b="50000"/></a:path></a:gradFill>')
    if e["shape"] == "pattern":
        return "<a:noFill/>"
    return solid(e["fill"], e.get("alpha", 1))


def line_xml(e):
    if e["shape"] == "pattern":
        return f'<a:ln w="{max(6350, emu(e["tile"]) // 60)}">{solid(e["line"], e["line_alpha"])}</a:ln>'
    if e.get("line") and e.get("line_w"):
        return f'<a:ln w="{emu(e["line_w"])}">{solid(e["line"], e.get("line_alpha", 1))}</a:ln>'
    return "<a:ln><a:noFill/></a:ln>"


def shape(e, sid):
    out = []
    if e["shape"] == "pattern":   # the panel colour under the pattern lines
        base = dict(e, shape="rect")
        out.append(_sp(sid, "Pattern panel", xfrm(base), geometry(base), solid(e["fill"]), "<a:ln><a:noFill/></a:ln>", ""))
        sid += 1
    out.append(_sp(sid, f"Shape {sid}", xfrm(e), geometry(e), fill_xml(e), line_xml(e), shadow(e.get("shadow"))))
    return "".join(out), sid + 1


def _sp(sid, name, xf, geom, fill, line, effects, txbody=""):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>{xf}{geom}{fill}{line}{effects}</p:spPr>{txbody}</p:sp>')


def text(e, sid, typeface, bold, italic):
    """A text box with one paragraph; the layout's lines are kept with line breaks."""
    algn = {"left": "l", "right": "r", "center": "ctr"}[e["align"]]
    size_pt = e["size"] * PT
    # A box with no Arabic letters (a number, an email) stays left to right, or PowerPoint
    # would show "96.4%" as "%96.4"; it keeps its right alignment.
    arabic = e["rtl"] and bool(ARABIC.search(e["text"]))
    rtl = ' rtl="1"' if arabic else ""
    lang = "ar-AE" if arabic else "en-US"
    attrs = f'lang="{lang}" sz="{int(round(size_pt * 100))}"'
    if bold:
        attrs += ' b="1"'
    if italic:
        attrs += ' i="1"'
    if e["tracking"]:
        attrs += f' spc="{int(round(e["tracking"] * size_pt * 100))}"'
    rpr = (f'<a:rPr {attrs} dirty="0">{solid(e["color"], e["alpha"])}'
           f'<a:latin typeface="{escape(typeface)}"/><a:cs typeface="{escape(typeface)}"/></a:rPr>')
    runs = []
    for i, line in enumerate(e["lines"]):
        if i:
            runs.append(f"<a:br>{rpr}</a:br>")
        runs.append(f"<a:r>{rpr}<a:t>{escape(BAD_XML.sub('', line))}</a:t></a:r>")
    line_space = int(round(size_pt * e["leading"] * 100))
    ppr = (f'<a:pPr algn="{algn}"{rtl}><a:lnSpc><a:spcPts val="{line_space}"/></a:lnSpc>'
           '<a:spcBef><a:spcPts val="0"/></a:spcBef><a:spcAft><a:spcPts val="0"/></a:spcAft></a:pPr>')
    body = (f'<p:txBody><a:bodyPr wrap="none" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t" rtlCol="0">'
            f'<a:noAutofit/></a:bodyPr><a:lstStyle/><a:p>{ppr}{"".join(runs)}'
            f'<a:endParaRPr {attrs}/></a:p></p:txBody>')
    name = f"{e.get('role', 'Text').capitalize()} {sid}"
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{sid}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>{xfrm(e)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>{body}</p:sp>'), sid + 1


def picture(e, sid, rid):
    return (f'<p:pic><p:nvPicPr><p:cNvPr id="{sid}" name="Logo {sid}"/><p:cNvPicPr><a:picLocks noChangeAspect="1"/>'
            f'</p:cNvPicPr><p:nvPr/></p:nvPicPr><p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch>'
            f'</p:blipFill><p:spPr>{xfrm(e)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>'), sid + 1
