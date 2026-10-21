"""Office previews must use embedded faces even when Office bundles an older font."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from xml.dom import minidom
import zipfile

import helpers  # noqa: F401
from deckcraft import check


PRESENTATION = "http://schemas.openxmlformats.org/presentationml/2006/main"
DRAWING = "http://schemas.openxmlformats.org/drawingml/2006/main"


class OfficeFontTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "Arabic [review].pptx"
        self.out = self.root / "pictures"
        self.out.mkdir()

    def package(self, embedded=True):
        font_list = ('<p:embeddedFontLst><p:embeddedFont><p:font typeface="Rubik"/>'
                     '<p:regular r:id="rId1"/><p:bold r:id="rId2"/></p:embeddedFont>'
                     '<p:embeddedFont><p:font typeface="Inter"/>'
                     '<p:regular r:id="rId3"/></p:embeddedFont></p:embeddedFontLst>') if embedded else ""
        parts = {
            "ppt/presentation.xml": (f'<p:presentation xmlns:p="{PRESENTATION}" '
                                     'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                                     f'{font_list}</p:presentation>').encode(),
            "ppt/slides/slide1.xml": (f'<p:sld xmlns:p="{PRESENTATION}" xmlns:a="{DRAWING}" '
                                      'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
                                      'xmlns:custom="urn:deckcraft:test" mc:Ignorable="custom" custom:note="Rubik">'
                                      '<a:latin typeface="Rubik"/><a:ea typeface="Rubik"/>'
                                      '<a:cs typeface="Inter"/><a:latin typeface="Arial"/>'
                                      '<a:t>Keep typeface="Rubik" and typeface="Inter" as text. مرحباً</a:t></p:sld>').encode(),
            "ppt/theme/theme1.xml": (f'<a:theme xmlns:a="{DRAWING}">'
                                      '<a:latin typeface="Rubik"/><a:cs typeface="Inter"/></a:theme>').encode(),
            "ppt/fonts/font1.fntdata": b"\0bundled Rubik regular\xff",
            "ppt/fonts/font2.fntdata": b"\0bundled Rubik bold\xfe",
            "ppt/fonts/font3.fntdata": b"\0bundled Inter\xfd",
            "opaque.bin": b"Rubik Inter <typeface> do not rewrite binary",
        }
        with zipfile.ZipFile(self.source, "w") as package:
            for name, data in parts.items():
                package.writestr(name, data)
        return parts

    def render(self):
        captured = {}

        def office(cmd, timeout):
            source = Path(cmd[-1])
            captured["path"] = source
            captured["bytes"] = source.read_bytes()
            with zipfile.ZipFile(source) as package:
                captured["parts"] = {name: package.read(name) for name in package.namelist()}
            folder = Path(cmd[cmd.index("--outdir") + 1])
            (folder / (source.stem + ".pdf")).write_bytes(b"fresh PDF")

        with patch.object(check, "find_office", return_value="office"), patch.object(
                check.shutil, "which", return_value=None), patch.object(check, "_run_tool", side_effect=office):
            pictures, problem = check.pptx_pictures(str(self.source), str(self.out), "review")
        self.assertIsNone(problem)
        self.assertEqual([Path(p).name for p in pictures], ["review.pdf"])
        self.assertEqual(Path(pictures[0]).read_bytes(), b"fresh PDF")
        return captured

    def test_embedded_names_are_isolated_consistently_in_a_private_render_copy(self):
        self.package()
        original = self.source.read_bytes()
        rendered = self.render()
        self.assertNotEqual(rendered["path"], self.source,
                            "Office needs a private font-isolated input to avoid its older bundled Rubik")
        self.assertEqual(rendered["path"].name, self.source.name)
        self.assertFalse(rendered["path"].exists(), "the renderer input should be cleaned with its profile")
        self.assertEqual(self.source.read_bytes(), original)
        presentation = minidom.parseString(rendered["parts"]["ppt/presentation.xml"])
        aliases = [node.getAttribute("typeface")
                   for node in presentation.getElementsByTagNameNS(PRESENTATION, "font")]
        self.assertEqual(len(set(aliases)), 2)
        self.assertTrue(all(alias not in {"Rubik", "Inter"} for alias in aliases))
        for name in ("ppt/slides/slide1.xml", "ppt/theme/theme1.xml"):
            doc = minidom.parseString(rendered["parts"][name])
            values = [node.getAttribute("typeface") for node in doc.getElementsByTagName("*")
                      if node.hasAttribute("typeface")]
            self.assertIn(aliases[0], values)
            self.assertIn(aliases[1], values)
            self.assertNotIn("Rubik", values)
            self.assertNotIn("Inter", values)

    def test_only_typeface_attributes_change_not_words_fonts_or_extension_namespaces(self):
        parts = self.package()
        rendered = self.render()["parts"]
        for name, data in parts.items():
            if not name.endswith(".xml"):
                self.assertEqual(rendered[name], data, name)
        slide = minidom.parseString(rendered["ppt/slides/slide1.xml"])
        self.assertEqual(slide.documentElement.getAttribute("custom:note"), "Rubik")
        self.assertEqual(slide.documentElement.getAttribute("xmlns:custom"), "urn:deckcraft:test")
        self.assertEqual(slide.documentElement.getAttribute("mc:Ignorable"), "custom")
        self.assertEqual(slide.getElementsByTagNameNS(DRAWING, "t")[0].firstChild.data,
                         'Keep typeface="Rubik" and typeface="Inter" as text. مرحباً')
        self.assertIn("Arial", [node.getAttribute("typeface")
                                for node in slide.getElementsByTagNameNS(DRAWING, "latin")])

    def test_unembedded_package_is_passed_to_office_unchanged(self):
        self.package(embedded=False)
        original = self.source.read_bytes()
        rendered = self.render()
        self.assertEqual(rendered["path"], self.source)
        self.assertEqual(rendered["bytes"], original)

    def test_malformed_xml_preserves_the_existing_office_fallback(self):
        self.package()
        with zipfile.ZipFile(self.source, "a") as package:
            package.writestr("ppt/slides/broken.xml", b"<p:broken")
        original = self.source.read_bytes()
        rendered = self.render()
        self.assertEqual(rendered["path"], self.source)
        self.assertEqual(rendered["bytes"], original)

    def test_separate_renders_do_not_reuse_font_aliases(self):
        self.package()
        one = self.render()["parts"]["ppt/presentation.xml"]
        two = self.render()["parts"]["ppt/presentation.xml"]
        self.assertNotEqual(one, two, "each Office profile needs its own embedded font names")


if __name__ == "__main__":
    unittest.main()
