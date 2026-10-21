"""Regression checks for real content at extraction and rendering boundaries."""
from pathlib import Path
import tempfile
import unittest

import helpers  # noqa: F401
from deckcraft import content, extract


class HtmlBlockExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source.html"

    def read(self, body):
        self.source.write_text("<h1>Title</h1>" + body, encoding="utf-8")
        return extract.read(str(self.source))

    def test_adjacent_block_elements_keep_separate_words(self):
        for tag in ("div", "section", "article", "header", "footer", "main", "aside",
                    "nav", "address", "dt", "dd", "pre", "h4", "h5", "h6"):
            with self.subTest(tag=tag):
                slides = self.read(f"<{tag}>First</{tag}><{tag}>Second</{tag}>")
                self.assertEqual(slides[0]["body"], ["First", "Second"])

    def test_nested_blocks_keep_visible_text_in_order(self):
        slides = self.read("<div>First<div>Second</div>Third</div>")
        self.assertEqual(slides[0]["body"], ["First", "Second", "Third"])

    def test_inline_markup_does_not_add_spaces_inside_words(self):
        slides = self.read("<div>Inter<strong>national</strong> freight</div>")
        self.assertEqual(slides[0]["body"], ["International freight"])

    def test_same_words_notices_a_word_lost_from_a_block(self):
        self.read("<div>First</div><div>Second</div>")
        changed = {"slides": [{"type": "title", "title": "Title", "subtitle": "First"}]}
        self.assertEqual(extract.same_words(str(self.source), changed), {"second": 1})

    def test_draft_from_blocks_is_valid_and_keeps_every_word(self):
        self.read("<div>First</div><div>Second</div><div>Third</div>")
        draft, _ = extract.draft(str(self.source))
        content.check(draft)
        self.assertEqual(extract.same_words(str(self.source), draft), {})
        self.assertIn("Third", str(draft))


if __name__ == "__main__":
    unittest.main()
