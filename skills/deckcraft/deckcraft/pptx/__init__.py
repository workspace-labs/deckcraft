"""Write a .pptx from laid-out slides, with the Python standard library only (ADR 0001)."""
import datetime
import os
import zipfile

from .. import designs
from .. import fonts as bundled
from . import fontfile, parts, shapes
from .parts import NS, XML, REL

SLOTS = {(False, False): "regular", (True, False): "bold", (False, True): "italic", (True, True): "boldItalic"}


def write(path, slides, design, content, fonts="design"):
    """Write the deck; returns a list of warnings.

    fonts="design" names each text's exact bundled font and embeds those fonts, so the deck looks
    the same on any computer. fonts="safe" uses plain fonts every computer has and embeds nothing.
    """
    lang = content["lang"]
    n = len(slides)
    files = {}
    media = []  # (zip name, source path)
    used = {}   # typeface -> {slot: font file path}
    warnings = []

    for i, slide in enumerate(slides, 1):
        xml, rels = _slide(slide, design, fonts, lang, media, used, warnings)
        files[f"ppt/slides/slide{i}.xml"] = xml
        files[f"ppt/slides/_rels/slide{i}.xml.rels"] = rels

    major = (_family(designs.font(design, "display", "en"), fonts), _family(designs.font(design, "display", "ar"), fonts))
    minor = (_family(designs.font(design, "body", "en"), fonts), _family(designs.font(design, "body", "ar"), fonts))
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    font_list, font_rels = _embed(used, files, n)
    extra = [("fntdata", "application/x-fontdata")] if used else []
    files.update({
        "[Content_Types].xml": parts.content_types(n, extra),
        "_rels/.rels": parts.root_rels(),
        "ppt/presentation.xml": parts.presentation(n, font_list, rtl=lang == "ar"),
        "ppt/_rels/presentation.xml.rels": parts.presentation_rels(n, font_rels),
        "ppt/slideMasters/slideMaster1.xml": parts.master(),
        "ppt/slideMasters/_rels/slideMaster1.xml.rels": parts.master_rels(),
        "ppt/slideLayouts/slideLayout1.xml": parts.layout(),
        "ppt/slideLayouts/_rels/slideLayout1.xml.rels": parts.layout_rels(),
        "ppt/theme/theme1.xml": parts.theme(design["name"], design["colors"], major, minor),
        "ppt/presProps.xml": parts.pres_props(),
        "ppt/viewProps.xml": parts.view_props(),
        "ppt/tableStyles.xml": parts.table_styles(),
        "docProps/core.xml": parts.core(content["title"], now),
        "docProps/app.xml": parts.app(n),
    })
    tmp = path + ".part"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", files.pop("[Content_Types].xml"))
        for name in sorted(files):
            z.writestr(name, files[name])
        for name, src in media:
            z.write(src, name)
    os.replace(tmp, path)
    return list(dict.fromkeys(warnings))


def _embed(used, files, n_slides):
    """Add each used font as EOT; returns (embeddedFontLst xml, relationships)."""
    if not used:
        return "", []
    entries, rels = [], []
    k = n_slides + 6  # after the slide, theme and props relationships
    for typeface in sorted(used):
        slots = ""
        for slot in ("regular", "bold", "italic", "boldItalic"):
            src = used[typeface].get(slot)
            if not src:
                continue
            k += 1
            name = f"font{k}.fntdata"
            with open(src, "rb") as f:
                files[f"ppt/fonts/{name}"] = fontfile.eot(f.read())
            rels.append((f"rId{k}", f"{REL}/font", f"fonts/{name}"))
            slots += f'<p:{slot} r:id="rId{k}"/>'
        entries.append(f'<p:embeddedFont><p:font typeface="{_xml(typeface)}" charset="0"/>{slots}</p:embeddedFont>')
    return "<p:embeddedFontLst>" + "".join(entries) + "</p:embeddedFontLst>", rels


def _xml(text):
    from xml.sax.saxutils import escape
    return escape(text, {'"': "&quot;"})


def _resolve(e, fonts, used, warnings):
    """(typeface, bold, italic) for a text element."""
    if fonts == "safe":
        return e["fallback"], e["weight"] >= 600, e["italic"]
    entry = bundled.lookup(e["family"], e["weight"], e["italic"])
    if not entry:
        warnings.append(f"The font {e['family']} is not bundled, so it is named but not carried in the PowerPoint.")
        return e["family"], e["weight"] >= 600, e["italic"]
    slot = SLOTS[(entry["bold"], entry["slanted"])]
    used.setdefault(entry["typeface"], {})[slot] = entry["path"]
    return entry["typeface"], entry["bold"], entry["slanted"]


def _family(f, fonts):
    return f["fallback"] if fonts == "safe" else f["family"]


def _slide(slide, design, fonts, lang, media, used, warnings):
    bg = designs.color(design, "bg")
    body, rels = [], [("rId1", f"{REL}/slideLayout", "../slideLayouts/slideLayout1.xml")]
    sid = 2
    for e in slide["elements"]:
        if e["kind"] == "shape":
            xml, sid = shapes.shape(e, sid)
        elif e["kind"] == "text":
            typeface, bold, italic = _resolve(e, fonts, used, warnings)
            xml, sid = shapes.text(e, sid, typeface, bold, italic)
        else:
            ext = os.path.splitext(e["path"])[1].lower().replace(".jpg", ".jpeg")
            name = f"ppt/media/image{len(media) + 1}{ext}"
            media.append((name, e["path"]))
            rid = f"rId{len(rels) + 1}"
            rels.append((rid, f"{REL}/image", "../media/" + os.path.basename(name)))
            xml, sid = shapes.picture(e, sid, rid)
        body.append(xml)
    tree = parts.EMPTY_TREE.replace("</p:spTree>", "".join(body) + "</p:spTree>")
    xml = (f'{XML}<p:sld {NS}><p:cSld><p:bg><p:bgPr>{shapes.solid(bg)}<a:effectLst/></p:bgPr></p:bg>'
           f'{tree}</p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')
    return xml, parts.rels(rels)
