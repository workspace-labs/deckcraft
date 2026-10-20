import os
import unittest

import helpers
from deckcraft import content, extract

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


class ExtractTests(unittest.TestCase):
    def test_pptx_made_by_powerpoint_keeps_every_word(self):
        src = os.path.join(FIX, "plain-clinic.pptx")
        data, report = extract.draft(src)
        content.check(data)
        self.assertEqual(report, [])
        self.assertEqual([s["type"] for s in data["slides"]], ["title", "points", "points", "closing"])
        self.assertEqual(data["slides"][0]["title"], "Clinic Opening Plan 2027")
        self.assertIn("Two doctors retire in 2027.", data["slides"][1]["points"])
        self.assertEqual(extract.same_words(src, data), {})

    def test_same_words_finds_a_lost_or_changed_word(self):
        src = os.path.join(FIX, "plain-clinic.pptx")
        data, _ = extract.draft(src)
        data["slides"][1]["points"][2] = "Two doctors leave in 2027."
        self.assertEqual(extract.same_words(src, data), {"retire": 1})

    def test_html_page(self):
        src = os.path.join(FIX, "plain-page.html")
        data, report = extract.draft(src)
        content.check(data)
        types = [s["type"] for s in data["slides"]]
        self.assertEqual(types, ["title", "points", "section", "closing"])
        self.assertEqual(data["slides"][0]["subtitle"], "A proposal for the community council, March 2027.")
        self.assertTrue(any("a picture" in r for r in report))
        self.assertTrue(any("a table (4 cells: Item, Cost, Soil and plants, AED 900,000)" in r for r in report))
        self.assertNotIn("not words", str(data))
        self.assertEqual(extract.same_words(src, data), {})

    def test_deckcraft_reads_its_own_pptx_back(self):
        import tempfile
        from deckcraft import designs, pptx
        from deckcraft.layout import layout_deck
        c = content.check(helpers.example("ar"))
        d = designs.load(9)
        slides, _ = layout_deck(c, d)
        path = os.path.join(tempfile.mkdtemp(), "back.pptx")
        pptx.write(path, slides, d, c)
        data, _ = extract.draft(path)
        self.assertEqual(data["lang"], "ar")
        self.assertEqual(data["slides"][0]["title"], "ثلاثة مراكز جديدة، وشبكة أسرع")

    def test_long_paragraph_is_split_at_sentences_not_cut(self):
        long = ("This is the first sentence of a long paragraph that goes on and on. " * 2).strip()
        slides = extract._points("T", [long, "Short point."])
        joined = " ".join(p for s in slides for p in s["points"])
        self.assertEqual(joined.split(), (long + " Short point.").split())


if __name__ == "__main__":
    unittest.main()
