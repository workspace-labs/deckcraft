"""Charts must retain supplied values and use finite geometry at numeric limits."""
import math
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

import helpers  # noqa: F401
from deckcraft import content, designs, html_page, html_slides, pptx
from deckcraft.layout import layout_deck


def chart(values, show=True, lang="en"):
    return content.check({"title": "Chart", "lang": lang, "slides": [
        {"type": "chart", "title": "Chart", "bars": [
            dict({"label": str(i + 1), "value": value}, **({"show": str(i + 1)} if show else {}))
            for i, value in enumerate(values)]}]})


class ChartValueTests(unittest.TestCase):
    def test_large_finite_values_match_ordinary_ratios_in_every_design(self):
        for lang in ("en", "ar"):
            for folder in designs.folders():
                with self.subTest(lang=lang, design=folder):
                    design = designs.load(folder)
                    ordinary, _ = layout_deck(chart([2, 1], lang=lang), design)
                    large, warnings = layout_deck(chart([1e308, 5e307], lang=lang), design)
                    self.assertEqual(warnings, [])
                    for expected, actual in zip(ordinary[0]["elements"], large[0]["elements"]):
                        for key in ("x", "y", "w", "h"):
                            self.assertTrue(math.isfinite(actual[key]), (key, actual))
                            self.assertAlmostEqual(expected[key], actual[key], places=6)

    def test_large_finite_page_values_keep_proportional_bars(self):
        page, _ = html_page.render(chart([1e308, 5e307]), designs.load(7))
        self.assertIn("--v:100.0%", page)
        self.assertIn("--v:50.0%", page)
        self.assertNotIn("--v:inf", page)

    def test_chart_values_beyond_finite_range_are_content_errors(self):
        for value in (10 ** 400, -(10 ** 400)):
            with self.subTest(value=str(value)[:8]):
                with self.assertRaises(content.ContentError):
                    chart([value, 1])

    def test_largest_finite_float_and_integer_make_finite_geometry(self):
        for value in (sys.float_info.max, 10 ** 308):
            with self.subTest(value=value):
                slides, _ = layout_deck(chart([value, 0]), designs.load(1))
                for element in slides[0]["elements"]:
                    self.assertTrue(all(math.isfinite(element[k]) for k in ("x", "y", "w", "h")))

    def test_implicit_labels_keep_fractional_precision_in_all_outputs(self):
        data = chart([1.25, 0.005], show=False)
        design = designs.load(7)
        slides, _ = layout_deck(data, design)
        labels = [e["text"] for e in slides[0]["elements"] if e.get("role") == "bar value"]
        self.assertEqual(labels, ["1.25", "0.005"])
        page, _ = html_page.render(data, design)
        slide_html = html_slides.render(slides, design, data)
        for label in labels:
            self.assertIn(">" + label + "<", page)
            self.assertIn(">" + label + "<", slide_html)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "chart.pptx"
            pptx.write(str(path), slides, design, data)
            with zipfile.ZipFile(path) as package:
                root = ET.fromstring(package.read("ppt/slides/slide1.xml"))
                words = [n.text for n in root.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}t")]
                for label in labels:
                    self.assertIn(label, words)

    def test_explicit_label_is_kept_exactly_as_supplied(self):
        data = chart([1.25, 2.5])
        data["slides"][0]["bars"][0]["show"] = "1.250 kg"
        slides, _ = layout_deck(data, designs.load(7))
        labels = [e["text"] for e in slides[0]["elements"] if e.get("role") == "bar value"]
        self.assertEqual(labels[0], "1.250 kg")

    def test_zero_and_tiny_values_make_finite_bars(self):
        for values in ([0, 0], [1e-300, 5e-301], [5e-324, sys.float_info.max]):
            with self.subTest(values=values):
                slides, _ = layout_deck(chart(values), designs.load(7))
                page, _ = html_page.render(chart(values), designs.load(7))
                self.assertNotIn("--v:inf", page)
                for element in slides[0]["elements"]:
                    self.assertTrue(all(math.isfinite(element[k]) for k in ("x", "y", "w", "h")))


if __name__ == "__main__":
    unittest.main()
