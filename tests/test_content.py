import copy
import json
import os
import tempfile
import unittest

import helpers
from deckcraft import content


class ContentTests(unittest.TestCase):
    def test_examples_are_valid(self):
        for lang in ("en", "ar"):
            c = content.check(helpers.example(lang))
            self.assertEqual(c["lang"], lang)

    def problems(self, data):
        with self.assertRaises(content.ContentError) as e:
            content.check(data)
        return e.exception.problems

    def test_unknown_field_is_named(self):
        d = helpers.example()
        d["slides"][0]["titel"] = "x"
        self.assertTrue(any('"titel" is not a known field' in p for p in self.problems(d)))

    def test_unknown_slide_type(self):
        d = helpers.example()
        d["slides"][1]["type"] = "table"
        self.assertTrue(any('"table" is not a slide type' in p for p in self.problems(d)))

    def test_limits_and_counts(self):
        d = helpers.example()
        d["slides"][0]["title"] = "x" * 91
        d["slides"][3]["points"] = ["only one"]
        d["slides"][4]["bars"][0]["value"] = "39"
        ps = self.problems(d)
        self.assertTrue(any("91 characters" in p for p in ps))
        self.assertTrue(any("2 to 6" in p for p in ps))
        self.assertTrue(any('"value" must be a number' in p for p in ps))
        self.assertEqual(len(ps), 3)

    def test_problems_are_all_reported_at_once(self):
        d = {"lang": "fr", "slides": []}
        ps = self.problems(d)
        self.assertGreaterEqual(len(ps), 3)

    def test_brand_checked(self):
        d = helpers.example()
        d["brand"] = {"accent": "blue", "logo": "logo.gif"}
        ps = self.problems(d)
        self.assertEqual(len(ps), 2)

    def test_bad_json_file(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            f.write("{ nope")
        try:
            with self.assertRaises(content.ContentError) as e:
                content.load(f.name)
            self.assertIn("not valid JSON", e.exception.problems[0])
        finally:
            os.unlink(f.name)


if __name__ == "__main__":
    unittest.main()
