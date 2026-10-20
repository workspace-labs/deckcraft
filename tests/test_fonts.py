import os
import re
import struct
import tempfile
import unittest
import zipfile

import helpers
from deckcraft import content, designs, fonts, pptx
from deckcraft.layout import layout_deck
from deckcraft.pptx import fontfile


class BundledFontTests(unittest.TestCase):
    def test_every_font_a_slide_uses_is_bundled_with_its_licence(self):
        for lang in ("en", "ar"):
            c = content.check(helpers.example(lang))
            for f in designs.folders():
                slides, _ = layout_deck(c, designs.load(f))
                for s in slides:
                    for e in s["elements"]:
                        if e["kind"] != "text":
                            continue
                        hit = [x for x in fonts.index() if x["family"] == e["family"] and
                               x["weight"] == e["weight"] and x["italic"] == bool(e["italic"])]
                        self.assertTrue(hit, f"{lang} {f}: {e['family']} {e['weight']} italic={e['italic']} not bundled")
        for x in fonts.index():
            self.assertTrue(os.path.isfile(os.path.join(fonts.FONTS_DIR, x["file"])), x["file"])
            lic = os.path.join(fonts.FONTS_DIR, "licences", x["family"].replace(" ", "") + "-OFL.txt")
            self.assertTrue(os.path.isfile(lic), lic)
            with open(lic, encoding="utf-8", errors="replace") as fh:
                self.assertIn("SIL OPEN FONT LICENSE", fh.read().upper())

    def test_eot_wraps_the_whole_font(self):
        x = fonts.lookup("Manrope", 800)
        with open(x["path"], "rb") as f:
            data = f.read()
        e = fontfile.eot(data)
        eot_size, font_size, version, flags = struct.unpack("<IIII", e[:16])
        self.assertEqual(eot_size, len(e))
        self.assertEqual(font_size, len(data))
        self.assertEqual(version, 0x00020001)
        self.assertEqual(flags, 0)
        self.assertEqual(struct.unpack("<H", e[34:36])[0], 0x504C)
        self.assertTrue(e.endswith(data))
        self.assertIn("Manrope ExtraBold".encode("utf-16-le"), e[:len(e) - len(data)])

    def test_lookup_names_each_weight_by_its_own_font_name(self):
        self.assertEqual(fonts.lookup("Manrope", 800)["typeface"], "Manrope ExtraBold")
        bold = fonts.lookup("Manrope", 700)
        self.assertEqual((bold["typeface"], bold["bold"]), ("Manrope", True))
        ital = fonts.lookup("Cormorant Garamond", 500, italic=True)
        self.assertTrue(ital["slanted"])
        self.assertIsNone(fonts.lookup("Comic Sans", 400))


class EmbeddingTests(unittest.TestCase):
    def make(self, lang, design, mode="design"):
        c = content.check(helpers.example(lang))
        d = designs.load(design)
        slides, _ = layout_deck(c, d)
        path = os.path.join(tempfile.mkdtemp(), "deck.pptx")
        warnings = pptx.write(path, slides, d, c, fonts=mode)
        return zipfile.ZipFile(path), warnings

    def test_every_typeface_on_a_slide_is_embedded(self):
        for lang, design in (("en", 8), ("ar", 8), ("ar", 9), ("en", 11)):
            z, warnings = self.make(lang, design)
            self.assertEqual(warnings, [])
            pres = z.read("ppt/presentation.xml").decode()
            self.assertIn('embedTrueTypeFonts="1"', pres)
            embedded = set(re.findall(r'<p:font typeface="([^"]+)"', pres))
            used = set()
            for n in z.namelist():
                if n.startswith("ppt/slides/slide"):
                    used |= set(re.findall(r'<a:latin typeface="([^"]+)"', z.read(n).decode()))
            self.assertEqual(used, embedded, f"{lang} {design}")
            self.assertIn("fntdata", z.read("[Content_Types].xml").decode())
            self.assertTrue(any(n.startswith("ppt/fonts/") for n in z.namelist()))

    def test_safe_fonts_embed_nothing(self):
        z, _ = self.make("en", 1, "safe")
        self.assertFalse(any(n.startswith("ppt/fonts/") for n in z.namelist()))
        self.assertNotIn("embeddedFontLst", z.read("ppt/presentation.xml").decode())


if __name__ == "__main__":
    unittest.main()
