"""The fixed parts of a .pptx package: one master, one blank layout, a theme and the props.

A .pptx is a zip of XML parts (ECMA-376). These are the smallest parts that
PowerPoint, Keynote and LibreOffice open without a repair prompt.
"""
from xml.sax.saxutils import escape

NS = ('xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"')
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "application/vnd.openxmlformats-officedocument.presentationml"

SLIDE_W, SLIDE_H = 12192000, 6858000  # 16:9, 13.333 x 7.5 inches


def rels(items):
    """items: [(id, type, target)]"""
    body = "".join(f'<Relationship Id="{i}" Type="{t}" Target="{escape(tg)}"/>' for i, t, tg in items)
    return f'{XML}<Relationships xmlns="{PKG}">{body}</Relationships>'


def content_types(n_slides, extra_defaults=()):
    defaults = [("rels", "application/vnd.openxmlformats-package.relationships+xml"),
                ("xml", "application/xml"), ("png", "image/png"), ("jpeg", "image/jpeg"),
                ("jpg", "image/jpeg")] + list(extra_defaults)
    overrides = [("/ppt/presentation.xml", f"{CT}.presentation.main+xml"),
                 ("/ppt/slideMasters/slideMaster1.xml", f"{CT}.slideMaster+xml"),
                 ("/ppt/slideLayouts/slideLayout1.xml", f"{CT}.slideLayout+xml"),
                 ("/ppt/theme/theme1.xml", "application/vnd.openxmlformats-officedocument.theme+xml"),
                 ("/ppt/presProps.xml", f"{CT}.presProps+xml"),
                 ("/ppt/viewProps.xml", f"{CT}.viewProps+xml"),
                 ("/ppt/tableStyles.xml", f"{CT}.tableStyles+xml"),
                 ("/docProps/core.xml", "application/vnd.openxmlformats-package.core-properties+xml"),
                 ("/docProps/app.xml", "application/vnd.openxmlformats-officedocument.extended-properties+xml")]
    overrides += [(f"/ppt/slides/slide{i}.xml", f"{CT}.slide+xml") for i in range(1, n_slides + 1)]
    d = "".join(f'<Default Extension="{e}" ContentType="{t}"/>' for e, t in defaults)
    o = "".join(f'<Override PartName="{p}" ContentType="{t}"/>' for p, t in overrides)
    return f'{XML}<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">{d}{o}</Types>'


def root_rels():
    return rels([("rId1", f"{REL}/officeDocument", "ppt/presentation.xml"),
                 ("rId2", "http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties",
                  "docProps/core.xml"),
                 ("rId3", f"{REL}/extended-properties", "docProps/app.xml")])


def presentation(n_slides, embedded_fonts_xml="", rtl=False):
    ids = "".join(f'<p:sldId id="{255 + i}" r:id="rId{i + 1}"/>' for i in range(1, n_slides + 1))
    rtl_attr = ' rtl="1"' if rtl else ""
    embed = ' embedTrueTypeFonts="1"' if embedded_fonts_xml else ""
    return (f'{XML}<p:presentation {NS}{embed}{rtl_attr}>'
            '<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>'
            f'<p:sldIdLst>{ids}</p:sldIdLst>'
            f'<p:sldSz cx="{SLIDE_W}" cy="{SLIDE_H}"/><p:notesSz cx="6858000" cy="9144000"/>'
            f'{embedded_fonts_xml}'
            '<p:defaultTextStyle><a:defPPr><a:defRPr lang="en-US"/></a:defPPr></p:defaultTextStyle>'
            '</p:presentation>')


def presentation_rels(n_slides, font_rels=()):
    items = [("rId1", f"{REL}/slideMaster", "slideMasters/slideMaster1.xml")]
    items += [(f"rId{i + 1}", f"{REL}/slide", f"slides/slide{i}.xml") for i in range(1, n_slides + 1)]
    k = n_slides + 2
    items += [(f"rId{k}", f"{REL}/theme", "theme/theme1.xml"),
              (f"rId{k + 1}", f"{REL}/presProps", "presProps.xml"),
              (f"rId{k + 2}", f"{REL}/viewProps", "viewProps.xml"),
              (f"rId{k + 3}", f"{REL}/tableStyles", "tableStyles.xml")]
    items += list(font_rels)
    return rels(items)


EMPTY_TREE = ('<p:spTree><p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
              '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/>'
              '<a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr></p:spTree>')


def master():
    lvl = '<a:lvl1pPr><a:defRPr sz="1800"/></a:lvl1pPr>'
    return (f'{XML}<p:sldMaster {NS}><p:cSld>{EMPTY_TREE}</p:cSld>'
            '<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" '
            'accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>'
            '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>'
            f'<p:txStyles><p:titleStyle>{lvl}</p:titleStyle><p:bodyStyle>{lvl}</p:bodyStyle>'
            f'<p:otherStyle>{lvl}</p:otherStyle></p:txStyles></p:sldMaster>')


def master_rels():
    return rels([("rId1", f"{REL}/slideLayout", "../slideLayouts/slideLayout1.xml"),
                 ("rId2", f"{REL}/theme", "../theme/theme1.xml")])


def layout():
    return (f'{XML}<p:sldLayout {NS} type="blank" preserve="1"><p:cSld name="Blank">{EMPTY_TREE}</p:cSld>'
            '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>')


def layout_rels():
    return rels([("rId1", f"{REL}/slideMaster", "../slideMasters/slideMaster1.xml")])


def theme(name, colors, major, minor):
    """colors: dict with bg, ink, accent, muted, surface, line (hex with #). major/minor: (latin, cs)."""
    def c(h):
        return f'<a:srgbClr val="{h[1:]}"/>'
    scheme = (f'<a:dk1>{c(colors["ink"])}</a:dk1><a:lt1>{c(colors["bg"])}</a:lt1>'
              f'<a:dk2>{c(colors["muted"])}</a:dk2><a:lt2>{c(colors["surface"])}</a:lt2>'
              f'<a:accent1>{c(colors["accent"])}</a:accent1><a:accent2>{c(colors["line"])}</a:accent2>'
              f'<a:accent3>{c(colors["muted"])}</a:accent3><a:accent4>{c(colors["ink"])}</a:accent4>'
              f'<a:accent5>{c(colors["accent"])}</a:accent5><a:accent6>{c(colors["line"])}</a:accent6>'
              f'<a:hlink>{c(colors["accent"])}</a:hlink><a:folHlink>{c(colors["muted"])}</a:folHlink>')

    def fonts(tag, pair):
        return (f'<a:{tag}><a:latin typeface="{escape(pair[0])}"/><a:ea typeface=""/>'
                f'<a:cs typeface="{escape(pair[1])}"/></a:{tag}>')
    solid = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    line = '<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln>'
    return (f'{XML}<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="{escape(name)}">'
            f'<a:themeElements><a:clrScheme name="{escape(name)}">{scheme}</a:clrScheme>'
            f'<a:fontScheme name="{escape(name)}">{fonts("majorFont", major)}{fonts("minorFont", minor)}</a:fontScheme>'
            f'<a:fmtScheme name="{escape(name)}"><a:fillStyleLst>{solid * 3}</a:fillStyleLst>'
            f'<a:lnStyleLst>{line * 3}</a:lnStyleLst>'
            '<a:effectStyleLst>' + '<a:effectStyle><a:effectLst/></a:effectStyle>' * 3 + '</a:effectStyleLst>'
            f'<a:bgFillStyleLst>{solid * 3}</a:bgFillStyleLst></a:fmtScheme></a:themeElements>'
            '<a:objectDefaults/><a:extraClrSchemeLst/></a:theme>')


def pres_props():
    return f'{XML}<p:presentationPr {NS}/>'


def view_props():
    return (f'{XML}<p:viewPr {NS}><p:normalViewPr><p:restoredLeft sz="15620"/><p:restoredTop sz="94660"/>'
            '</p:normalViewPr><p:gridSpacing cx="76200" cy="76200"/></p:viewPr>')


def table_styles():
    return (f'{XML}<a:tblStyleLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'def="{5C22544A-7EE6-4342-B048-85BDC9FD1C3A}"/>')


def core(title, created):
    return (f'{XML}<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" '
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
            f'<dc:title>{escape(title)}</dc:title><dc:creator>deckcraft</dc:creator>'
            f'<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
            f'<dcterms:modified xsi:type="dcterms:W3CDTF">{created}</dcterms:modified></cp:coreProperties>')


def app(n_slides):
    return (f'{XML}<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" '
            'xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">'
            f'<Application>deckcraft</Application><Slides>{n_slides}</Slides><PresentationFormat>Widescreen</PresentationFormat>'
            '</Properties>')
