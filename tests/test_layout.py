import unittest

import helpers
from deckcraft import content, designs, textfit
from deckcraft.layout import SLIDE_H, layout_deck

EPS = 0.05


def overlap(a, b):
    return (min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]) > EPS and
            min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]) > EPS)


class LayoutTests(unittest.TestCase):
    def decks(self):
        for lang in ("en", "ar"):
            c = content.check(helpers.example(lang))
            for f in designs.folders():
                d = designs.load(f)
                slides, warnings = layout_deck(c, d)
                yield lang, f, slides, warnings

    def test_examples_fit_without_warnings(self):
        for lang, f, slides, warnings in self.decks():
            self.assertEqual(warnings, [], f"{lang} {f}")

    def test_everything_stays_on_the_slide(self):
        for lang, f, slides, _ in self.decks():
            for n, s in enumerate(slides, 1):
                for e in s["elements"]:
                    if e.get("deco"):
                        continue
                    where = f"{lang} {f} slide {n} {e.get('role', e['kind'])}"
                    self.assertGreaterEqual(e["x"], -EPS, where)
                    self.assertLessEqual(e["x"] + e["w"], 100 + EPS, where)
                    self.assertGreaterEqual(e["y"], -EPS, where)
                    self.assertLessEqual(e["y"] + e["h"], SLIDE_H + EPS, where)

    def test_no_text_runs_into_other_text(self):
        for lang, f, slides, _ in self.decks():
            for n, s in enumerate(slides, 1):
                texts = [e for e in s["elements"] if e["kind"] == "text"]
                for i, a in enumerate(texts):
                    for b in texts[i + 1:]:
                        self.assertFalse(overlap(a, b),
                                         f"{lang} {f} slide {n}: {a['role']} '{a['text'][:20]}' meets {b['role']} '{b['text'][:20]}'")

    def test_arabic_is_the_english_layout_mirrored(self):
        c = content.check(helpers.example("ar"))
        d = designs.load(9)
        slides, _ = layout_deck(c, d)
        pattern = [e for e in slides[0]["elements"] if e.get("shape") == "pattern"][0]
        self.assertAlmostEqual(pattern["x"], 0)              # the panel moves to the left
        texts = [e for e in slides[0]["elements"] if e["kind"] == "text"]
        self.assertTrue(all(e["rtl"] for e in texts))
        self.assertTrue(all(e["align"] in ("right", "center") for e in texts))
        self.assertTrue(all(e["tracking"] == 0 for e in texts))  # spacing breaks Arabic joining

    def test_long_text_is_shrunk_then_reported(self):
        c = content.check(helpers.example())
        c["slides"][0]["title"] = "A very long title " * 8
        slides, warnings = layout_deck(c, designs.load(2))
        self.assertTrue(any(w.startswith("Slide 1: the title") for w in warnings), warnings)
        c["slides"][0]["title"] = "Three new hubs and a much faster freight network"
        _, warnings = layout_deck(c, designs.load(2))
        self.assertEqual(warnings, [])

    def test_auto_number_row_stays_on_slide_at_content_limits(self):
        for lang, value in (("en", "AED 1234567890123456"),
                            ("ar", "١٢٣٤٥٦٧٨٩٠١٢٣٤٥٦٧٨٩٠")):
            c = content.check({"lang": lang, "title": "Report", "slides": [
                {"type": "numbers", "title": "Report", "items": [
                    {"value": value, "label": "Delivery centres opened across locations"}
                    for _ in range(4)]}]})
            slides, warnings = layout_deck(c, designs.load(12))
            for e in slides[0]["elements"]:
                if e["kind"] == "text":
                    self.assertGreaterEqual(e["x"], -EPS, (lang, e))
                    self.assertLessEqual(e["x"] + e["w"], 100 + EPS, (lang, e))
            # Four full-length values cannot remain at the approved display size.
            self.assertTrue(any("number" in w for w in warnings), lang)

    def test_arabic_numeral_overflow_is_reported(self):
        c = content.check({"lang": "ar", "title": "تقرير", "slides": [
            {"type": "numbers", "title": "تقرير", "items": [
                {"value": "١٢٣٤٥٦٧٨٩٠١٢٣٤٥٦٧٨٩٠", "label": "الشحن"}
                for _ in range(4)]}]})
        _, warnings = layout_deck(c, designs.load(5))
        self.assertTrue(any("number is too long" in w for w in warnings), warnings)


class TextFitTests(unittest.TestCase):
    def test_arabic_numerals_are_not_measured_as_joined_letters(self):
        # The widest bundled Arabic numeral is 0.803 em (Alexandria Bold).
        # Amiri's narrow letter average previously understated its digit widths.
        for digits in ("٠١٢٣٤٥٦٧٨٩", "۰۱۲۳۴۵۶۷۸۹"):
            self.assertGreaterEqual(textfit.text_width(digits, 1, 0.412), 8.4)

    def test_wrap_keeps_every_word(self):
        text = "one two three four five six seven"
        lines = textfit.wrap(text, 2, 0.5, 6)
        self.assertGreater(len(lines), 1)
        self.assertEqual(" ".join(lines), text)

    def test_fit_shrinks(self):
        size, lines, ok = textfit.fit("word " * 30, 5, 0.5, 40, 20, 1.2)
        self.assertTrue(ok)
        self.assertLess(size, 5)
        self.assertLessEqual(len(lines) * size * 1.2, 20 + 1e-6)


if __name__ == "__main__":
    unittest.main()
