import pathlib
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

import helpers
from deckcraft import content, extract


class ExtractionRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def source(self, html):
        path = pathlib.Path(self.tmp.name) / "source.html"
        path.write_text(html, encoding="utf-8")
        return str(path)

    def test_final_two_paragraphs_are_both_carried(self):
        path = self.source("<h1>Start</h1><h2>Close</h2><p>Keep this.</p><p>Lost forever.</p>")
        draft, report = extract.draft(path)
        content.check(draft)
        self.assertEqual(extract.same_words(path, draft), {})
        self.assertIn("Lost forever.", str(draft))
        self.assertEqual(report, [])

    def test_repeated_word_counts_accumulate_before_normalization(self):
        path = self.source("<h1>Title</h1><p>go go.</p>")
        changed = {"slides": [{"type": "title", "title": "Title", "subtitle": "go"}]}
        self.assertEqual(extract.same_words(path, changed), {"go": 1})

    def test_arabic_repeated_words_ignore_only_sentence_punctuation(self):
        path = self.source("<h1>Title</h1><p>عِلْم، عِلْم.</p>")
        changed = {"slides": [{"type": "title", "title": "Title", "subtitle": "عِلْم"}]}
        self.assertEqual(extract.same_words(path, changed), {"عِلْم": 1})

    def test_case_is_ignored_without_losing_repetition_counts(self):
        path = self.source("<h1>TITLE</h1><p>GO, go. GO</p>")
        changed = {"slides": [{"type": "title", "title": "title", "subtitle": "go go go"}]}
        self.assertEqual(extract.same_words(path, changed), {})

    def test_arabic_diacritics_and_internal_numeric_punctuation_are_preserved(self):
        for before, after in [("عِلْم", "علم"), ("1,000", "1000"), ("1.25", "125")]:
            with self.subTest(before=before):
                path = self.source("<h1>Title</h1><p>" + before + "</p>")
                changed = {"slides": [{"type": "title", "title": "Title", "subtitle": after}]}
                self.assertEqual(extract.same_words(path, changed), {before: 1})

    def test_table_notice_does_not_overwrite_picture_notice(self):
        path = self.source('<h1>T</h1><table><tr><td><img src="x.png">A</td></tr></table>')
        read = extract.read(path)
        self.assertEqual(read[0]["other"], ["a table (1 cells: A)", "a picture"])

    def test_unmatched_table_closing_tag_is_ignored(self):
        path = self.source("<h1>T</h1></table><p>Keep this.</p>")
        read = extract.read(path)
        self.assertEqual(read[0]["title"], "T")
        self.assertEqual(read[0]["body"], ["Keep this."])
        self.assertEqual(read[0]["other"], [])

    def test_nested_tables_keep_separate_omission_notices(self):
        path = self.source("<h1>T</h1><table><tr><td>Outer<table><tr><td>Inner</td></tr></table>"
                           "After</td></tr></table>")
        read = extract.read(path)
        self.assertEqual(read[0]["other"], ["a table (2 cells: Outer, After)", "a table (1 cells: Inner)"])

    def test_attached_speaker_notes_are_reported_as_uncarried(self):
        fixture = pathlib.Path(__file__).parent / "fixtures" / "plain-clinic.pptx"
        path = pathlib.Path(self.tmp.name) / "with-notes.pptx"
        rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
        ct_ns = "http://schemas.openxmlformats.org/package/2006/content-types"
        with zipfile.ZipFile(fixture) as src, zipfile.ZipFile(path, "w") as dst:
            for item in src.infolist():
                data = src.read(item.filename)
                if item.filename == "ppt/slides/_rels/slide1.xml.rels":
                    root = ET.fromstring(data)
                    ET.SubElement(root, "{" + rel_ns + "}Relationship", {
                        "Id": "rId999", "Type": extract.R[1:-1] + "/notesSlide",
                        "Target": "../notesSlides/notesSlide1.xml"})
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif item.filename == "[Content_Types].xml":
                    root = ET.fromstring(data)
                    ET.SubElement(root, "{" + ct_ns + "}Override", {
                        "PartName": "/ppt/notesSlides/notesSlide1.xml",
                        "ContentType": "application/vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"})
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                dst.writestr(item, data)
            notes = ('<p:notes xmlns:p="' + extract.P[1:-1] + '" xmlns:a="' + extract.A[1:-1] + '">'
                     '<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r>'
                     '<a:t>Speaker reminder</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:notes>')
            dst.writestr("ppt/notesSlides/notesSlide1.xml", notes)
        draft, report = extract.draft(str(path))
        self.assertTrue(any("Slide 1: speaker notes could not be carried" in line for line in report))
        self.assertNotIn("Speaker reminder", str(draft))

    def test_html_line_break_keeps_word_boundary(self):
        path = self.source("<h1>Hello<br>world</h1><p>First<br>second</p>")
        read = extract.read(path)
        self.assertEqual(read[0]["title"], "Hello world")
        self.assertEqual(read[0]["body"], ["First second"])


class ContentBoundaryRegressionTests(unittest.TestCase):
    def test_non_string_slide_types_become_content_errors(self):
        for kind in [[], {}, None, False, 1]:
            with self.subTest(kind=kind):
                with self.assertRaises(content.ContentError):
                    content.check({"title": "T", "slides": [{"type": kind, "title": "T"}]})

    def test_non_finite_chart_values_are_rejected(self):
        for value in [float("nan"), float("inf"), float("-inf")]:
            with self.subTest(value=value):
                with self.assertRaises(content.ContentError):
                    content.check({"title": "T", "slides": [{"type": "chart", "title": "T", "bars": [
                        {"label": "A", "value": value}, {"label": "B", "value": 1}]}]})

    def test_xml_forbidden_characters_are_rejected_in_all_text_paths(self):
        for bad in ["\x00", "\x01", "\ud800", "\ufffe", "\uffff"]:
            cases = [
                {"title": "Hi" + bad, "slides": [{"type": "title", "title": "T"}]},
                {"title": "T", "org": "Hi" + bad, "slides": [{"type": "title", "title": "T"}]},
                {"title": "T", "slides": [{"type": "points", "title": "T", "points": ["Hi" + bad, "Fine"]}]},
                {"title": "T", "slides": [{"type": "numbers", "title": "T", "items": [
                    {"value": "1" + bad, "label": "A"}, {"value": "2", "label": "B"}]}]},
            ]
            for case in cases:
                with self.subTest(bad=repr(bad), case=repr(case)):
                    with self.assertRaises(content.ContentError):
                        content.check(case)

    def test_xml_legal_whitespace_is_kept_as_given(self):
        title = "Line one\nLine two\tTab\rReturn"
        checked = content.check({"title": title, "slides": [{"type": "title", "title": title}]})
        self.assertEqual(checked["title"], title)


if __name__ == "__main__":
    unittest.main()
