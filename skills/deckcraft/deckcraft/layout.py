"""Lay out every slide as plain shapes, texts and images (ADR 0002).

Units: 1 = 1% of the slide width; a 16:9 slide is 100 x 56.25. Everything is laid
out left to right; an Arabic deck is the same layout mirrored at the end, so the
PowerPoint and the HTML slides writers never think about direction.
"""
from . import designs, textfit
from .content import chart_label
from .images import image_size

SLIDE_H = 56.25


def layout_deck(content, design, base_dir="."):
    """Returns (slides, warnings). Each slide is {"type", "elements"}."""
    slides, warnings = [], []
    count = len(content["slides"])
    for i, s in enumerate(content["slides"], 1):
        b = Builder(design, content, i, count, base_dir)
        b.decorations()
        getattr(b, "slide_" + s["type"])(s)
        b.org_line()
        b.logo()
        els = b.els
        if content["lang"] == "ar":
            els = [mirror(e) for e in els]
        slides.append({"type": s["type"], "elements": els})
        warnings += b.warnings
    return slides, warnings


def mirror(e):
    """The same element on a right-to-left slide."""
    e = dict(e)
    e["x"] = round(100 - e["x"] - e["w"], 3)
    if e.get("rotate"):
        e["rotate"] = -e["rotate"]
    if e.get("shadow"):
        e["shadow"] = dict(e["shadow"], dx=-e["shadow"]["dx"])
    if e["kind"] == "text":
        e["rtl"] = True
        e["align"] = {"left": "right", "right": "left"}.get(e["align"], e["align"])
    swap = {"tr-bl": "tl-br", "tl-br": "tr-bl"}
    if e.get("corners") in swap:
        e["corners"] = swap[e["corners"]]
    return e


class Builder:
    def __init__(self, design, content, index, count, base_dir):
        self.d = design
        self.s = design["slide"]
        self.lang = content["lang"]
        self.content = content
        self.index, self.count = index, count
        self.base_dir = base_dir
        self.els, self.warnings = [], []
        self.ax, self.ay, self.aw, self.ah = self.s["area"]
        self.center = self.s["align"] == "center"
        org = self.s["org"]
        pos = org["pos"] if (content.get("org") or org["pos"] == "footnote") else "none"
        self.org_pos = pos
        room = {"bottom-left": org["size"] * 2.6, "bottom-right": org["size"] * 2.6,
                "footnote": 3.4}.get(pos, 0)
        self.bottom = self.ay + self.ah - room

    # ---- small helpers -------------------------------------------------
    def c(self, name):
        return designs.color(self.d, name)

    def font(self, role, weight=None, italic=False):
        f = designs.font(self.d, role, self.lang)
        w = designs.weight(f["family"], weight or f["weight"])
        return {"family": f["family"], "fallback": f["fallback"], "weight": w,
                "italic": bool(italic) and self.lang != "ar", "width": f["width"]}

    def shape(self, shape, x, y, w, h, fill=None, alpha=1, line=None, line_alpha=1, line_w=0, **extra):
        e = {"kind": "shape", "shape": shape, "x": x, "y": y, "w": w, "h": h,
             "fill": self.c(fill), "alpha": alpha, "line": self.c(line), "line_alpha": line_alpha,
             "line_w": line_w}
        e.update(extra)
        self.els.append(e)
        return e

    def make_text(self, text, w, max_h, st, role, size=None, color=None, align=None,
                  min_scale=0.5, max_lines=None, weight=None, italic=None, leading=None):
        """A text element (not yet placed) sized to fit w x max_h."""
        f = self.font(st.get("font", "body"), weight or st.get("weight"),
                      st.get("italic") if italic is None else italic)
        upper = st.get("case") == "upper" and self.lang == "en"
        if upper:
            text = text.upper()
        tracking = 0 if self.lang == "ar" else st.get("tracking", 0)
        lead = leading or st.get("leading", 1.25)
        if self.lang == "ar":
            lead = max(lead, 1.35)  # Arabic letters reach higher and lower than Latin ones
        fw = f["width"] * (1.06 if self.lang == "ar" else 1)  # Arabic shapes vary more
        size = size or st["size"]
        s, lines, ok = textfit.fit(text, size, fw, w, max_h, lead, tracking, min_scale, max_lines)
        if not ok:
            self.warnings.append(f"Slide {self.index}: the {role} is too long to fit; shorten it.")
        elif role in ("title", "quote") and s < size * 0.7:
            self.warnings.append(f"Slide {self.index}: the {role} had to be made much smaller to fit; "
                                 "a shorter one will look better.")
        if align is None:
            align = "center" if self.center else "left"
        return {"kind": "text", "role": role, "text": text, "lines": lines, "x": 0, "y": 0, "w": w,
                "h": round(len(lines) * s * lead, 3), "size": round(s, 3), "leading": lead,
                "tracking": tracking, "color": self.c(color or st.get("color", "ink")), "alpha": 1,
                "align": align, "valign": "top", "rtl": False, "rotate": 0, **f}

    def place(self, e, x, y):
        e["x"], e["y"] = round(x, 3), round(y, 3)
        self.els.append(e)
        return e

    def x_for(self, w):
        return self.ax + (self.aw - w) / 2 if self.center else self.ax

    def stack(self, items, top, bottom, pos):
        """Place [(gap_before, element)] as one block between top and bottom."""
        total = sum(g + e["h"] for g, e in items)
        if pos == "bottom":
            y = bottom - total
        elif pos == "top":
            y = top
        else:
            y = top + (bottom - top - total) / 2
        y = max(top, y)
        for g, e in items:
            y += g
            self.place(e, self.x_for(e["w"]), y)
            y += e["h"]
        return y

    def label_style(self):
        return self.s["label"]

    def sub_style(self):
        b = self.s["body"]
        return {"font": "body", "size": b["size"] * 1.15, "color": "muted", "leading": 1.35}

    # ---- every slide -----------------------------------------------------
    def decorations(self):
        for dec in self.s["deco"]:
            dec = dict(dec)
            shape = dec.pop("shape")
            x, y, w, h = dec.pop("x"), dec.pop("y"), dec.pop("w"), dec.pop("h")
            fill = dec.pop("fill", None)
            self.shape(shape, x, y, w, h, fill=fill, deco=True,
                       **{k: (self.c(v) if k == "line" else v) for k, v in dec.items()})

    def eyebrow(self, text):
        """Draw the small line above a title; returns the y below it."""
        st = self.s["eyebrow"]
        size = st["size"]
        y = self.ay
        if not text:
            return y
        if st["mark"]:
            m = size * 0.9
            mx = self.ax + (self.aw - m) / 2 if self.center else self.ax + st["indent"]
            self.shape("diamond", mx, y, m, m, fill=st["mark_color"])
            y += m + size * 0.6
        e = self.make_text(text, self.aw * 0.8, size * 1.4, st, "eyebrow", max_lines=1, min_scale=0.7,
                           leading=1.25)
        fw = e["width"]
        tw = min(textfit.text_width(e["text"], e["size"], fw, e["tracking"]) * 1.08 + 0.4, self.aw * 0.8)
        if st["style"] == "text":
            e["w"] = tw if not self.center else self.aw * 0.8
            x = self.x_for(e["w"]) + (0 if self.center else st["indent"])
            self.place(e, x, y)
            return y + e["h"] + size * 1.6
        padx, pady = size * 0.85, size * 0.38
        bw, bh = tw + 2 * padx, e["h"] + 2 * pady
        x = self.x_for(bw) + (0 if self.center else st["indent"])
        radius = bh / 2 if st["style"] == "pill" else 0
        self.shape("rect", x, y, bw, bh, fill=st["fill"], alpha=st["alpha"], line=st["line"],
                   line_alpha=st["line_alpha"], line_w=0.08 if st["line"] else 0, radius=radius,
                   rotate=st["rotate"])
        e["w"], e["align"], e["rotate"] = tw, "center", st["rotate"]
        self.place(e, x + padx, y + pady)
        return y + bh + size * 1.6

    def org_line(self):
        org = self.s["org"]
        text = self.content.get("org", "")
        pos = self.org_pos
        if pos == "none":
            return
        size = org["size"]
        bottom = self.ay + self.ah
        if pos == "footnote":
            self.shape("rect", self.ax, bottom - 2.3, self.aw, 0.08, fill="line")
            st = {"font": "display", "size": size, "color": "muted", "italic": True, "weight": 400}
            if text:
                e = self.make_text(text, self.aw * 0.8, size * 1.4, st, "footnote", max_lines=1, align="left")
                self.place(e, self.ax, bottom - 1.6)
            n = self.make_text(str(self.index), 4, size * 1.4, st, "page number", max_lines=1, align="right")
            self.place(n, self.ax + self.aw - 4, bottom - 1.6)
            return
        e = self.make_text(text, self.aw * 0.5, size * 1.4, org, "organisation name", max_lines=1)
        if pos == "top-right":
            e["align"] = "right"
            self.place(e, self.ax + self.aw * 0.5, self.ay)
        elif pos == "bottom-right":
            e["align"] = "right"
            self.place(e, self.ax + self.aw * 0.5, bottom - e["h"])
        else:
            if self.center:
                e["w"] = self.aw
            self.place(e, self.x_for(e["w"]), bottom - e["h"])

    def logo(self):
        path = (self.content.get("brand") or {}).get("logo")
        if not path:
            return
        import os
        full = path if os.path.isabs(path) else os.path.join(self.base_dir, path)
        try:
            iw, ih = image_size(full)
        except (OSError, ValueError) as err:
            self.warnings.append(f"The logo cannot be used: {err}")
            return
        h = 3.2
        w = min(h * iw / ih, 14)
        h = w * ih / iw
        # Top right, unless the organisation name already sits there.
        y = self.ay + self.ah - h if self.org_pos == "top-right" else self.ay
        self.els.append({"kind": "image", "path": full, "x": self.ax + self.aw - w, "y": y, "w": w, "h": h,
                         "rotate": 0})

    # ---- slide types ---------------------------------------------------
    def slide_title(self, s, size_k=1.2, last=None):
        y = self.eyebrow(s.get("eyebrow"))
        t = self.s["title"]
        w = self.aw * t["w"]
        room = self.bottom - y
        size = t["size"] * size_k
        rest = []
        if s.get("subtitle"):
            st = self.sub_style()
            rest.append((st["size"] * 0.9, self.make_text(s["subtitle"], min(w, self.aw * 0.75), room * 0.3,
                                                          st, "subtitle")))
        if last:
            rest.append(last)
        elif s.get("note"):
            st = self.label_style()
            rest.append((st["size"] * 1.8, self.make_text(s["note"], w, st["size"] * 3, st, "note")))
        # The title takes whatever room the lines under it leave.
        title_room = min(room * 0.72, room - sum(g + e["h"] for g, e in rest))
        items = [(0, self.make_text(s["title"], w, title_room, t, "title", size=size))] + rest
        self.stack(items, y, self.bottom, t["pos"] if t["pos"] != "top" else "middle")

    def slide_section(self, s):
        self.slide_title(s, size_k=1.05)

    def slide_closing(self, s):
        last = None
        if s.get("contact"):
            b = self.s["body"]
            st = {"font": "body", "size": b["size"] * 1.1, "color": "accent", "weight": 700}
            last = (b["size"] * 1.8, self.make_text(s["contact"], self.aw * 0.8, b["size"] * 3, st, "contact"))
        self.slide_title({k: v for k, v in s.items() if k != "contact"}, size_k=1.0, last=last)

    def heading(self, s, y, k=0.78):
        """A content slide's title at the top; returns the y below it."""
        t = self.s["title"]
        w = self.aw * min(1, t["w"] + 0.1)
        e = self.make_text(s["title"], w, (self.bottom - y) * 0.34, t, "title", size=t["size"] * k)
        self.place(e, self.x_for(w), y)
        return y + e["h"]

    def slide_points(self, s):
        y = self.heading(s, self.eyebrow(s.get("eyebrow")))
        b = self.s["body"]
        y += b["size"] * 2
        width = self.aw * (0.72 if self.center else 0.92)
        x0 = self.ax + (self.aw - width) / 2 if self.center else self.ax
        mk = b["size"] * 1.7
        avail = self.bottom - y
        size = b["size"]
        for _ in range(12):
            texts = [self.make_text(p, width - mk, avail, b, "point", size=size, align="left", min_scale=1)
                     for p in s["points"]]
            gap = size * 0.85
            total = sum(e["h"] for e in texts) + gap * (len(texts) - 1)
            if total <= avail or size <= b["size"] * 0.6:
                break
            size *= 0.93
        if total > avail:
            self.warnings.append(f"Slide {self.index}: the points are too long to fit; shorten them or split the slide.")
        y = max(y, y + (avail - total) / 2 if self.center else y)
        mst = self.s["marker"]
        for i, e in enumerate(texts):
            self.marker(mst, i, x0, y, e["size"], e["leading"])
            self.place(e, x0 + mk, y)
            y += e["h"] + gap

    def marker(self, mst, i, x, y, size, leading):
        mid = y + size * leading / 2
        style = mst["style"]
        if style == "num":
            st = {"font": "display", "size": size, "color": mst["color"], "weight": 700}
            e = self.make_text(f"{i + 1}.", size * 1.4, size * 2, st, "marker", align="left", leading=leading)
            self.place(e, x, y)
        elif style == "dash":
            self.shape("rect", x, mid - size * 0.06, size * 0.8, size * 0.12, fill=mst["color"])
        else:
            m = size * (0.42 if style == "dot" else 0.38 if style == "square" else 0.55)
            shape = {"dot": "ellipse", "square": "rect", "diamond": "diamond"}[style]
            self.shape(shape, x + size * 0.1, mid - m / 2, m, m, fill=mst["color"])

    def slide_numbers(self, s):
        y = self.eyebrow(s.get("eyebrow"))
        layout = self.s["numbers"]
        t = self.s["title"]
        if layout == "column-right":
            col_w = self.aw * 0.34
            self.number_column(s["items"], self.ax + self.aw - col_w, self.ay, col_w)
            w = self.aw * t["w"]
            e = self.make_text(s["title"], w, (self.bottom - y) * 0.6, t, "title")
            self.place(e, self.ax, self.bottom - e["h"])
            return
        if layout == "table":
            y = self.heading(s, y, k=1.0)
            self.number_table(s["items"], y + self.s["body"]["size"] * 2.2)
            return
        top = self.number_row(s["items"], self.bottom)
        w = self.aw * t["w"]
        gap = t["size"] * 0.8
        e = self.make_text(s["title"], w, top - gap - y, t, "title")
        self.stack([(0, e)], y, top - gap, t["pos"])

    def number_texts(self, it, i, w, align):
        v, l = self.s["value"], self.label_style()
        cs = self.s["cards"]
        color = v["first"] if (i == 0 and v["first"]) else v["color"]
        if cs["style"] == "sticker" and cs["inks"]:
            color = cs["inks"][i % len(cs["inks"])]
        ve = self.make_text(it["value"], w, v["size"] * 1.3, v, "number", color=color, align=align,
                            max_lines=1, min_scale=0.55, leading=1.15)
        lcolor = color if cs["style"] == "sticker" else l["color"]
        le = self.make_text(it["label"], w, l["size"] * 2.8, l, "number label", color=lcolor, align=align,
                            max_lines=2, min_scale=0.8)
        return ve, le

    def number_row(self, items, bottom):
        """Cards in a row ending at bottom; returns the top y."""
        cs = self.s["cards"]
        style = cs["style"]
        n = len(items)
        pad = cs["pad"] if style in ("box", "panel", "sticker") else 0
        gap = {"panel": 0, "box": 2.4, "sticker": 3}.get(style, 3)
        indent = cs["line_w"] + 1.4 if style == "rule-left" else 0
        auto = self.s["numbers"] == "row-auto"
        align = "center" if (self.center or style == "divider") else "left"
        vsize = self.s["value"]["size"]
        if auto:
            gap = 7
            widths = [max(textfit.text_width(it["value"], vsize, self.font("display")["width"] * 1.04),
                          textfit.text_width(it["label"], self.label_style()["size"], self.font("body")["width"]))
                      + 1 for it in items]
            available = self.aw - gap * (n - 1)
            total = sum(widths)
            if total > available:
                widths = [w * available / total for w in widths]
        else:
            cw = (self.aw - gap * (n - 1)) / n
            widths = [cw] * n
        cells = []
        for i, it in enumerate(items):
            inner = widths[i] - 2 * pad - indent
            cells.append(self.number_texts(it, i, inner, align))
        vh = max(c[0]["h"] for c in cells)
        lh = max(c[1]["h"] for c in cells)
        inner_gap = 0.5
        card_h = pad * 2 + vh + inner_gap + lh
        extra = cs["line_w"] + 1.6 if style == "rule" else (cs["line_w"] + 1.2 if style == "rule-top" else 0)
        top = bottom - card_h - extra
        x = self.ax if not (self.center and auto) else self.ax + (self.aw - sum(widths) - gap * (n - 1)) / 2
        if style == "rule":
            self.shape("rect", self.ax, top, self.aw, cs["line_w"], fill=cs["line"])
        if style == "panel":
            self.shape("rect", self.ax, top, self.aw, card_h, fill=cs["fill"], alpha=cs["alpha"],
                       line=cs["line"], line_alpha=cs["line_alpha"], line_w=0.1, radius=cs["radius"],
                       shadow={"dx": 0, "dy": 1.2, "blur": 3, "color": "#504090", "alpha": 0.12})
        cy = top + extra
        for i, (ve, le) in enumerate(cells):
            w = widths[i]
            if style == "box":
                self.shape("rect", x, cy, w, card_h, fill=cs["fill"], alpha=cs["alpha"], radius=cs["radius"],
                           shadow={"dx": 0, "dy": 1, "blur": 2.5, "color": "#A05A32", "alpha": 0.12} if cs["shadow"] else None)
            elif style == "sticker":
                fills = cs["fills"] or [cs["fill"]]
                rot = cs["rotate"][i % len(cs["rotate"])] if cs["rotate"] else 0
                self.shape("rect", x, cy, w, card_h, fill=fills[i % len(fills)], line=cs["line"], line_w=cs["line_w"],
                           radius=cs["radius"], rotate=rot,
                           shadow={"dx": 0.6, "dy": 0.6, "blur": 0, "color": self.c(cs["line"]), "alpha": 1})
                ve["rotate"] = le["rotate"] = rot
            elif style == "rule-top":
                self.shape("rect", x, top, w, cs["line_w"], fill=cs["line"])
            elif style == "rule-left":
                self.shape("rect", x, cy, cs["line_w"], card_h, fill=cs["line"])
            if style in ("divider", "panel") and i > 0:
                c = cs["divider"] if style == "panel" else cs["line"]
                a = cs["divider_alpha"] if style == "panel" else cs["line_alpha"]
                self.shape("rect", x - gap / 2 - 0.04, cy + (pad or 0), 0.08, card_h - 2 * pad, fill=c, alpha=a)
            self.place(ve, x + pad + indent, cy + pad)
            self.place(le, x + pad + indent, cy + pad + vh + inner_gap)
            x += w + gap
        return top

    def number_column(self, items, x, y, w):
        for i, it in enumerate(items):
            ve, le = self.number_texts(it, i, w, "right")
            self.place(ve, x, y)
            self.place(le, x, y + ve["h"] + 0.2)
            y += ve["h"] + 0.2 + le["h"] + 1.4

    def number_table(self, items, y):
        w = self.aw * 0.62
        x = self.x_for(w)
        self.shape("rect", x, y, w, 0.2, fill="ink")
        y += 0.2
        v, l = self.s["value"], self.label_style()
        for i, it in enumerate(items):
            ve = self.make_text(it["value"], w * 0.4, v["size"] * 1.3, v, "number", align="right", max_lines=1,
                                min_scale=0.6, leading=1.15)
            le = self.make_text(it["label"], w * 0.58, l["size"] * 2.8, l, "number label", align="left", max_lines=2)
            row = max(ve["h"], le["h"]) + 1.8
            self.place(le, x, y + (row - le["h"]) / 2)
            self.place(ve, x + w * 0.6, y + (row - ve["h"]) / 2)
            y += row
            self.shape("rect", x, y, w, 0.08, fill="line")

    def slide_chart(self, s):
        y = self.heading(s, self.eyebrow(s.get("eyebrow")))
        bst, l, v = self.s["bars"], self.label_style(), self.s["value"]
        bottom = self.bottom
        if s.get("note"):
            ne = self.make_text(s["note"], self.aw, l["size"] * 2.8, l, "note", max_lines=2)
            bottom -= ne["h"] + 1
            self.place(ne, self.x_for(ne["w"]), bottom + 1)
        lab_h = l["size"] * 1.3
        base_y = bottom - lab_h - 0.8
        val_size = max(1.4, v["size"] * 0.45)
        top = y + 2.5 + val_size * 1.3
        width = self.aw * (0.8 if self.center else 0.9)
        x0 = self.x_for(width)
        bars = s["bars"]
        slot = width / len(bars)
        bw = slot * 0.62
        biggest = max(b["value"] for b in bars) or 1
        for i, b in enumerate(bars):
            h = max(0.3, (base_y - top) * (b["value"] / biggest))
            bx = x0 + i * slot + (slot - bw) / 2
            fill = bst["last"] if i == len(bars) - 1 else bst["fill"]
            self.shape("rect", bx, base_y - h, bw, h, fill=fill, radius=bst["radius"],
                       line=bst["line"], line_w=0.15 if bst["line"] else 0, corners="top")
            shown = chart_label(b)
            vst = dict(v, size=val_size)
            ve = self.make_text(shown, slot, val_size * 1.3, vst, "bar value", align="center", max_lines=1,
                                min_scale=0.6, leading=1.15)
            self.place(ve, x0 + i * slot, base_y - h - ve["h"] - 0.4)
            le = self.make_text(b["label"], slot, lab_h, l, "bar label", align="center", max_lines=1, min_scale=0.6)
            self.place(le, x0 + i * slot, base_y + 0.8)
        if bst["base"]:
            self.shape("rect", x0, base_y, width, 0.15, fill=bst["base"])

    def slide_quote(self, s):
        t = self.s["title"]
        mark_size = 9
        mark = "“" if self.lang == "en" else "«"
        st = {"font": "display", "size": mark_size, "color": "accent", "leading": 1}
        me = self.make_text(mark, mark_size, mark_size, st, "quote mark", max_lines=1)
        w = self.aw * 0.82
        qst = {"font": "display", "size": t["size"] * 0.62, "color": t["color"], "leading": 1.3,
               "italic": t["italic"], "weight": None}
        qe = self.make_text(s["text"], w, (self.bottom - self.ay) * 0.6, qst, "quote")
        items = [(0, me), (0, qe)]
        if s.get("by"):
            l = self.label_style()
            items.append((l["size"] * 1.6, self.make_text("— " + s["by"], w, l["size"] * 2.8, l, "quote name")))
        self.stack(items, self.ay, self.bottom, "middle")
