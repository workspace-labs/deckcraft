"""Read someone's existing .pptx or .html into a draft content file, keeping every word.

The draft maps their slides onto deckcraft slide types (a starting point the agent may
re-map, never re-word). Anything that cannot be carried (tables, pictures, charts, notes)
is listed, never dropped silently. same_words() proves no word was lost.
"""
import collections
import html.parser
import posixpath
import re
import zipfile

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
P = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
ARABIC = re.compile("[؀-ۿ]")
QUOTES = ("“", "\"", "«", "”")


CONTACT = re.compile(r"^([^@\s]+@[^@\s]+\.\S+|https?://\S+|www\.\S+)$")


def read(path):
    """[{"title": str, "body": [str], "other": [what could not be carried]}] in slide order."""
    if path.lower().endswith(".pptx"):
        return _read_pptx(path)
    if path.lower().endswith((".html", ".htm")):
        with open(path, encoding="utf-8", errors="replace") as f:
            return _read_html(f.read())
    raise ValueError("deckcraft reads .pptx and .html files.")


def draft(path):
    """(content dict, report lines) for a file."""
    slides = read(path)
    words = " ".join(s["title"] + " " + " ".join(s["body"]) for s in slides)
    lang = "ar" if len(ARABIC.findall(words)) > len(re.findall(r"[A-Za-z]", words)) else "en"
    out, report = [], []
    for n, s in enumerate(slides, 1):
        title, body = s["title"].strip(), [b.strip() for b in s["body"] if b.strip()]
        if not title and body:
            title, body = body[0], body[1:]
        for o in s["other"]:
            report.append(f"Slide {n}: {o} could not be carried; tell the person.")
        if not title:
            continue
        if n == 1:
            slide = {"type": "title", "title": title}
            if body:
                slide["subtitle"] = body.pop(0)
            if body:
                slide["note"] = body.pop(0)
            out.append(slide)
            if body:
                out += _points(title, body)
        elif not body:
            out.append({"type": "closing" if n == len(slides) else "section", "title": title})
        elif n == len(slides) and len(body) <= 2 and (len(body) == 1 or CONTACT.match(body[-1])):
            slide = {"type": "closing", "title": title}
            if CONTACT.match(body[-1]):
                slide["contact"] = body.pop()
            if body:
                slide["subtitle"] = body[0]
            out.append(slide)
        elif len(body) == 1:
            out.append({"type": "section", "title": title, "subtitle": body[0]})
        else:
            out += _points(title, body)
    for n, s in enumerate(out, 1):
        for k, v in s.items():
            if isinstance(v, str) and len(v) > 140 and k != "text":
                report.append(f"Draft slide {n}: the {k} is {len(v)} characters, longer than a slide holds; "
                              "ask the person how to shorten it.")
        for p in s.get("points", []):
            if len(p) > 140:
                report.append(f"Draft slide {n}: a point is {len(p)} characters; ask the person how to shorten it.")
    title = slides[0]["title"] if slides and slides[0]["title"] else "Untitled"
    return {"lang": lang, "title": title[:90], "slides": out}, report


def _points(title, body):
    """Points slides of up to 6 points with the same title; a paragraph too long for one point is split
    at its sentences (the words stay the same)."""
    parts = []
    for b in body:
        sentences = re.split(r"(?<=[.!?؟])\s+", b) if len(b) > 140 else [b]
        parts += [x for x in sentences if x]
    if len(parts) == 1:
        return [{"type": "section", "title": title, "subtitle": parts[0]}]
    chunks = [parts[i:i + 6] for i in range(0, len(parts), 6)]
    if len(chunks) > 1 and len(chunks[-1]) == 1:
        chunks[-2], chunks[-1] = chunks[-2][:-1], chunks[-2][-1:] + chunks[-1]
    return [{"type": "points", "title": title, "points": c} for c in chunks]


def same_words(original, content):
    """Words in the original file that the content file no longer has (with counts)."""
    def words(text):
        # Normalize each occurrence before counting: punctuation variants must add,
        # rather than overwrite one another's repetition counts.
        return collections.Counter(re.sub(r"[.,،؛؟]+$", "", w.lower())
                                   for w in re.findall(r"[\w؀-ۿ%.,'-]+", text)
                                   if re.search(r"\w", w))
    src = " ".join(s["title"] + " " + " ".join(s["body"]) for s in read(original))
    have = []
    for s in content["slides"]:
        for k, v in s.items():
            if k == "type":
                continue
            if isinstance(v, str):
                have.append(v)
            elif isinstance(v, list):
                for x in v:
                    have += [x] if isinstance(x, str) else [str(y) for y in x.values()]
    missing = words(src) - words(" ".join(have))
    return dict(missing)


# ---- PowerPoint ---------------------------------------------------------------
def _read_pptx(path):
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(path)
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    rels = _rels(z, "ppt/_rels/presentation.xml.rels")
    order = [rels[s.get(R + "id")] for s in pres.iter(P + "sldId")]
    slides = []
    for part in order:
        slide_part = posixpath.join("ppt", part)
        root = ET.fromstring(z.read(slide_part))
        title, body, other = "", [], []
        slide_rels = posixpath.join(posixpath.dirname(slide_part), "_rels", posixpath.basename(slide_part) + ".rels")
        if slide_rels in z.namelist():
            attached = ET.fromstring(z.read(slide_rels))
            if any(r.get("Type", "").endswith("/notesSlide") for r in attached):
                other.append("speaker notes")
        best = None
        for sp in root.iter(P + "sp"):
            ph = sp.find(f"{P}nvSpPr/{P}nvPr/{P}ph")
            paras = [_para(p) for p in sp.iter(A + "p")]
            paras = [x for x in paras if x.strip()]
            if not paras:
                continue
            kind = ph.get("type") if ph is not None else None
            if kind in ("title", "ctrTitle") and not title:
                title = " ".join(paras)
                continue
            size = max([int(r.get("sz")) for r in sp.iter(A + "rPr") if r.get("sz")] or [0])
            body.append((size, paras))
            if best is None or size > best[0]:
                best = (size, paras)
        if not title and best and best[0] >= 2800:   # no title placeholder: the biggest text is the title
            body.remove(best)
            title = " ".join(best[1])
        flat = [p for _, paras in body for p in paras]
        for gf in root.iter(P + "graphicFrame"):
            if gf.find(f".//{A}tbl") is not None:
                cells = [_para(p) for p in gf.iter(A + "p") if _para(p).strip()]
                other.append(f"a table ({len(cells)} cells: {', '.join(cells[:4])}{'...' if len(cells) > 4 else ''})")
            else:
                other.append("a chart or diagram")
        pics = sum(1 for _ in root.iter(P + "pic"))
        if pics:
            other.append(f"{pics} picture(s)")
        slides.append({"title": title, "body": flat, "other": other})
    return slides


def _para(p):
    out = []
    for node in p.iter():
        if node.tag == A + "t" and node.text:
            out.append(node.text)
        elif node.tag == A + "br":
            out.append(" ")
    return re.sub(r"\s+", " ", "".join(out)).strip()


def _rels(z, name):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(z.read(name))
    return {r.get("Id"): r.get("Target").lstrip("/").replace("ppt/", "", 1) for r in root}


# ---- HTML -------------------------------------------------------------------------
class _Html(html.parser.HTMLParser):
    BLOCKS = {"h1", "h2", "h3", "p", "li", "blockquote", "td", "th", "figcaption"}
    SKIP = {"head", "script", "style", "noscript", "template", "svg"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.slides, self.buf, self.tag, self.skip = [], [], None, 0
        self.tables = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag == "br" and not self.skip:
            self.buf.append(" ")
        elif tag == "table":
            self._flush()
            slide = self._slide()
            self.tables.append((slide, len(slide["other"]), []))
            slide["other"].append("a table")
        elif tag == "img":
            self._slide()["other"].append("a picture")
        elif tag in self.BLOCKS:
            self._flush()
            self.tag = tag

    def handle_endtag(self, tag):
        if tag in self.SKIP:
            self.skip = max(0, self.skip - 1)
        elif tag == "table":
            if not self.tables:
                return
            self._flush()
            slide, notice, cells = self.tables.pop()
            shown = ", ".join(cells[:4]) + ("..." if len(cells) > 4 else "")
            slide["other"][notice] = f"a table ({len(cells)} cells: {shown})"
        elif tag in self.BLOCKS:
            self._flush()

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)

    def _slide(self):
        if not self.slides:
            self.slides.append({"title": "", "body": [], "other": []})
        return self.slides[-1]

    def _flush(self):
        text = re.sub(r"\s+", " ", "".join(self.buf)).strip()
        self.buf = []
        tag, self.tag = self.tag, None
        if not text:
            return
        if tag in ("h1", "h2") or (tag == "h3" and not self._slide()["title"]):
            self.slides.append({"title": text, "body": [], "other": []})
        elif self.tables:
            self.tables[-1][2].append(text)
        else:
            self._slide()["body"].append(text)


def _read_html(text):
    p = _Html()
    p.feed(text)
    p.close()
    p._flush()
    return [s for s in p.slides if s["title"] or s["body"] or s["other"]]
