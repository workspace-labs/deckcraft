import os
import re
import tempfile
import unittest
import zipfile
from xml.dom import minidom

import helpers
from deckcraft import cli, content, designs, html_page, html_slides, pptx
from deckcraft.layout import layout_deck


class PptxTests(unittest.TestCase):
    def build(self, lang, design, fonts="design"):
        c = content.check(helpers.example(lang))
        d = designs.load(design)
        slides, _ = layout_deck(c, d)
        path = os.path.join(self.tmp, f"{lang}-{design}-{fonts}.pptx")
        pptx.write(path, slides, d, c, fonts=fonts)
        return path, len(slides)

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_every_design_makes_a_well_formed_package(self):
        for lang in ("en", "ar"):
            for f in designs.folders():
                path, n = self.build(lang, f)
                z = zipfile.ZipFile(path)
                names = set(z.namelist())
                self.assertEqual(z.namelist()[0], "[Content_Types].xml")
                for name in names:
                    if name.endswith((".xml", ".rels")):
                        minidom.parseString(z.read(name))
                types = z.read("[Content_Types].xml").decode()
                for i in range(1, n + 1):
                    self.assertIn(f"/ppt/slides/slide{i}.xml", types)
                    self.assertIn(f"ppt/slides/slide{i}.xml", names)
                # every relationship points at a part that exists
                for name in names:
                    if name.endswith(".rels"):
                        base = os.path.dirname(os.path.dirname(name))
                        for target in re.findall(r'Target="([^"]+)"', z.read(name).decode()):
                            full = os.path.normpath(os.path.join(base, target)).replace(os.sep, "/")
                            self.assertIn(full, names, f"{name} -> {target}")

    def test_arabic_text_is_right_to_left(self):
        path, _ = self.build("ar", 5)
        xml = zipfile.ZipFile(path).read("ppt/slides/slide1.xml").decode()
        self.assertIn('rtl="1"', xml)
        self.assertIn('lang="ar-AE"', xml)
        self.assertIn('typeface="Amiri"', xml)

    def test_safe_fonts(self):
        path, _ = self.build("en", 10, fonts="safe")
        xml = zipfile.ZipFile(path).read("ppt/slides/slide1.xml").decode()
        self.assertNotIn("Bricolage", xml)
        self.assertIn('typeface="Arial Black"', xml)

    def test_text_is_escaped(self):
        c = content.check(helpers.example())
        c["slides"][0]["title"] = 'Tom & "Jerry" <b>'
        d = designs.load(1)
        slides, _ = layout_deck(c, d)
        path = os.path.join(self.tmp, "esc.pptx")
        pptx.write(path, slides, d, c)
        minidom.parseString(zipfile.ZipFile(path).read("ppt/slides/slide1.xml"))


class HtmlTests(unittest.TestCase):
    def test_arabic_pages_keep_the_same_upright_type_as_arabic_slides(self):
        for number in (2, 8, 11):
            d = designs.load(number)
            page, _ = html_page.render(content.check(helpers.example("ar")), d)
            self.assertIn("--title-style:normal", page)
            self.assertIn("[lang=ar] .lead,[lang=ar] .cards span,[lang=ar] footer{font-style:normal}", page)

    def test_slides_and_page(self):
        for lang in ("en", "ar"):
            c = content.check(helpers.example(lang))
            for f in designs.folders():
                d = designs.load(f)
                slides, _ = layout_deck(c, d)
                html = html_slides.render(slides, d, c)
                self.assertEqual(html.count('<section class="slide"'), len(c["slides"]))
                page, warnings = html_page.render(c, d)
                self.assertEqual(warnings, [])
                self.assertEqual(page.count('<section class="block'), len(c["slides"]))
                self.assertEqual(page.count("<h1>"), 1)
                if lang == "ar":
                    self.assertIn('dir="rtl"', html)
                    self.assertIn('dir="rtl"', page)

    def test_html_is_escaped(self):
        c = content.check(helpers.example())
        c["slides"][0]["title"] = "<script>alert(1)</script>"
        d = designs.load(4)
        slides, _ = layout_deck(c, d)
        for html in (html_slides.render(slides, d, c), html_page.render(c, d)[0]):
            self.assertNotIn("<script>alert", html)
            self.assertIn("&lt;script&gt;", html)


class CliTests(unittest.TestCase):
    def test_output_name_cannot_escape_output_folder(self):
        with tempfile.TemporaryDirectory() as root:
            out = os.path.join(root, "out")
            src = os.path.join(helpers.EXAMPLES, "northwind-en.json")
            for name in ("../escape", "..\\escape", os.path.join(root, "absolute"), "C:\\escape"):
                with self.subTest(name=name):
                    self.assertEqual(cli.main(["make", src, "--design", "7", "--out", out,
                                               "--formats", "slides", "--name", name]), 1)
            self.assertFalse(os.path.exists(out))
            self.assertEqual(os.listdir(root), [])

    def test_make_all_three(self):
        out = tempfile.mkdtemp()
        src = os.path.join(helpers.EXAMPLES, "northwind-en.json")
        self.assertEqual(cli.main(["make", src, "--design", "7", "--out", out, "--name", "deck"]), 0)
        self.assertEqual(sorted(os.listdir(out)), ["deck-page.html", "deck-slides.html", "deck.pptx"])

    def test_bad_content_and_design_are_refused(self):
        out = tempfile.mkdtemp()
        bad = os.path.join(out, "bad.json")
        with open(bad, "w") as f:
            f.write('{"title": "x", "slides": [{"type": "nope"}]}')
        self.assertEqual(cli.main(["make", bad, "--design", "1", "--out", out]), 1)
        src = os.path.join(helpers.EXAMPLES, "northwind-en.json")
        self.assertEqual(cli.main(["make", src, "--design", "99", "--out", out]), 1)
        self.assertEqual(os.listdir(out), ["bad.json"])


if __name__ == "__main__":
    unittest.main()
