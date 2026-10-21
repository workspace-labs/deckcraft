"""Malformed logo headers must become warnings while all requested files are made."""
import base64
import contextlib
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest

import helpers  # noqa: F401
from deckcraft import cli, content, designs, html_page
from deckcraft.images import image_size
from deckcraft.layout import layout_deck


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
JPEG = base64.b64decode(
    "/9j/wAALCAABAAEBAREA/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9"
    "AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpT"
    "VFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJ"
    "ytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/9sAQwACAgICAgIDAgIDBQMDAwUGBQUFBQYIBgYGBgYICggI"
    "CAgICAoKCgoKCgoKDAwMDAwMDg4ODg4PDw8PDw8PDw8P/90ABAAB/9oACAEBAAA/APwDr//Z")


class LogoTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def logo(self, raw, suffix=".png"):
        path = self.root / ("logo" + suffix)
        path.write_bytes(raw)
        return path

    def data(self, logo):
        return content.check({"title": "Report", "brand": {"logo": str(logo)},
                              "slides": [{"type": "title", "title": "Report"}]})

    def test_truncated_png_headers_are_value_errors(self):
        for length in (8, 16, 20, 23):
            with self.subTest(length=length):
                with self.assertRaises(ValueError):
                    image_size(str(self.logo(PNG[:length])))

    def test_truncated_jpeg_headers_are_value_errors(self):
        for raw in (b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xc0\x00\x11\x08\x00"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    image_size(str(self.logo(raw, ".jpg")))

    def test_zero_dimensions_are_value_errors(self):
        for width, height in ((0, 1), (1, 0), (0, 0)):
            with self.subTest(size=(width, height)):
                raw = PNG[:16] + struct.pack(">II", width, height) + PNG[24:]
                with self.assertRaises(ValueError):
                    image_size(str(self.logo(raw)))

    def test_bad_logo_is_reported_and_omitted_in_slides_and_page(self):
        data = self.data(self.logo(PNG[:8]))
        design = designs.load(1)
        slides, warnings = layout_deck(data, design)
        self.assertTrue(any("logo cannot be used" in w for w in warnings))
        self.assertFalse(any(e["kind"] == "image" for e in slides[0]["elements"]))
        page, page_warnings = html_page.render(data, design)
        self.assertTrue(any("logo cannot be used" in w for w in page_warnings))
        self.assertNotIn('class="logo', page)

    def test_page_also_rejects_invalid_logo_without_slide_layout(self):
        page, warnings = html_page.render(self.data(self.logo(PNG[:8])), designs.load(1))
        self.assertTrue(any("logo cannot be used" in w for w in warnings))
        self.assertNotIn('class="logo', page)

    def test_make_finishes_all_formats_and_reports_bad_logo(self):
        for name, raw in (("short", PNG[:8]), ("zero", PNG[:16] + b"\0" * 8 + PNG[24:])):
            with self.subTest(name=name):
                path = self.root / (name + ".json")
                path.write_text(json.dumps(self.data(self.logo(raw))), encoding="utf-8")
                output = self.root / name
                with contextlib.redirect_stdout(io.StringIO()) as log:
                    status = cli.main(["make", str(path), "--design", "1", "--out", str(output)])
                self.assertEqual(status, 0)
                self.assertIn("logo cannot be used", log.getvalue())
                self.assertEqual(len(list(output.iterdir())), 3)

    def test_valid_png_dimensions_and_embedding_are_preserved(self):
        path = self.logo(PNG)
        self.assertEqual(image_size(str(path)), (1, 1))
        data = self.data(path)
        slides, warnings = layout_deck(data, designs.load(1))
        self.assertEqual(warnings, [])
        self.assertEqual(sum(e["kind"] == "image" for e in slides[0]["elements"]), 1)
        page, warnings = html_page.render(data, designs.load(1))
        self.assertEqual(warnings, [])
        self.assertIn("data:image/png;base64," + base64.b64encode(PNG).decode(), page)

    def test_valid_jpeg_marker_padding_keeps_logo_in_every_output(self):
        for padding in (0, 1, 3):
            with self.subTest(padding=padding):
                raw = JPEG[:2] + b"\xff" * padding + JPEG[2:]
                path = self.logo(raw, ".jpg")
                self.assertEqual(image_size(str(path)), (1, 1))
                data = self.data(path)
                slides, warnings = layout_deck(data, designs.load(1))
                self.assertEqual(warnings, [])
                self.assertTrue(any(e["kind"] == "image" for e in slides[0]["elements"]))
                page, warnings = html_page.render(data, designs.load(1))
                self.assertEqual(warnings, [])
                self.assertIn("data:image/jpeg;base64," + base64.b64encode(raw).decode(), page)

    def test_truncated_jpeg_marker_padding_is_reported(self):
        with self.assertRaises(ValueError):
            image_size(str(self.logo(b"\xff\xd8\xff\xff\xff", ".jpg")))


if __name__ == "__main__":
    unittest.main()
