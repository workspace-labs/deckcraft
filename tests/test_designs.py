import os
import re
import unittest
from urllib.parse import parse_qs, urlsplit

import helpers  # noqa: F401
from deckcraft import content, designs
from deckcraft.layout import layout_deck


class DesignTests(unittest.TestCase):
    def test_twelve_designs_load(self):
        folders = designs.folders()
        self.assertEqual(len(folders), 12)
        for i, f in enumerate(folders, 1):
            d = designs.load(f)
            self.assertEqual(d["id"], f"{i:02d}")
            self.assertTrue(d["css"].strip(), f"{f} has no style.css")
            self.assertEqual(designs.check(d), [])

    def test_find_by_number_slug_and_name(self):
        self.assertEqual(designs.find("3"), "03-nature-earth")
        self.assertEqual(designs.find("03"), "03-nature-earth")
        self.assertEqual(designs.find("gulf-heritage"), "09-gulf-heritage")
        self.assertEqual(designs.find("Playful Pop"), "10-playful-pop")
        with self.assertRaises(designs.DesignError):
            designs.find("13")

    def test_every_font_is_known_and_requested_weights_exist(self):
        for f in designs.folders():
            d = designs.load(f)
            url = designs.google_fonts_url(d)
            for fam, spec in re.findall(r"family=([^:&]+):([^&]+)", url):
                fam = fam.replace("+", " ")
                self.assertIn(fam, designs.AVAILABLE, f"{f}: {fam} has no weight table")
                weights = [int(x.split(",")[-1]) for x in spec.split("@")[1].split(";")]
                for w in weights:
                    self.assertIn(w, designs.AVAILABLE[fam], f"{f}: {fam} has no weight {w}")

    def test_requested_fonts_cover_every_rendered_text_variant(self):
        for f in designs.folders():
            d = designs.load(f)
            requested = set()
            query = parse_qs(urlsplit(designs.google_fonts_url(d)).query)
            for family_spec in query["family"]:
                family, spec = family_spec.split(":")
                axes, tuples = spec.split("@")
                for values in tuples.split(";"):
                    variant = dict(zip(axes.split(","), map(int, values.split(","))))
                    requested.add((family, variant["wght"], bool(variant.get("ital", 0))))
            for lang in ("en", "ar"):
                with self.subTest(design=f, lang=lang):
                    slides, _ = layout_deck(content.check(helpers.example(lang)), d)
                    used = {(e["family"], e["weight"], e["italic"])
                            for slide in slides for e in slide["elements"] if e["kind"] == "text"}
                    self.assertFalse(used - requested, f"Missing web fonts: {sorted(used - requested)}")

    def test_every_colour_name_used_exists(self):
        for f in designs.folders():
            d = designs.load(f)
            s = d["slide"]
            names = [s["title"]["color"], s["eyebrow"]["color"], s["value"]["color"], s["label"]["color"],
                     s["org"]["color"], s["marker"]["color"], s["bars"]["fill"], s["bars"]["last"]]
            names += [x["fill"] for x in s["deco"] if x.get("fill")] + list(s["cards"]["fills"])
            for n in names:
                designs.color(d, n)  # raises if unknown

    def test_brand_accent_replaces_accent(self):
        d = designs.load(1, {"accent": "#0055AA"})
        self.assertEqual(designs.color(d, "accent"), "#0055AA")

    def test_picker_page_shows_twelve(self):
        with open(os.path.join(designs.DESIGNS_DIR, "picker.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertEqual(len(re.findall(r"\{n:'", html)), 12)


if __name__ == "__main__":
    unittest.main()
