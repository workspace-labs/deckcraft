"""The checker must report fresh evidence, never reuse a previous successful run."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import helpers  # noqa: F401
from deckcraft import check


class CheckTests(unittest.TestCase):
    def test_batch_inputs_with_same_basename_keep_separate_evidence(self):
        other = self.root / "second"
        other.mkdir()
        one = self.root / "deck.html"
        two = other / "deck.html"
        one.write_text('<section class="slide">First</section>')
        two.write_text('<section class="slide">Second</section>')
        seen = []

        def render(path, folder, stem):
            picture = Path(folder) / (stem + "-01.png")
            picture.write_bytes(Path(path).read_bytes())
            seen.append(picture)
            return [str(picture)], None

        with patch.object(check, "html_pictures", side_effect=render), contextlib.redirect_stdout(io.StringIO()):
            result = check.run([str(one), str(two)], str(self.out))
        self.assertEqual(result, 0)
        self.assertEqual(len(set(seen)), 2)
        self.assertIn(b"First", seen[0].read_bytes())
        self.assertIn(b"Second", seen[1].read_bytes())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.out = self.root / "check"
        self.out.mkdir()
        self.html = self.root / 'current #1 & "draft".html'
        self.html.write_text('<section class="slide">Current content</section>')

    def test_failed_browser_does_not_reuse_old_picture(self):
        stale = self.out / "current-01.png"
        stale.write_bytes(b"old picture")
        with patch.object(check, "find_browser", return_value="browser"), patch.object(
                check, "BrowserSession", side_effect=subprocess.CalledProcessError(1, "browser")):
            pictures, problem = check.html_pictures(str(self.html), str(self.out), "current")
        self.assertEqual(pictures, [])
        self.assertTrue(problem)
        self.assertEqual(stale.read_bytes(), b"old picture")

    def test_failed_office_does_not_reuse_old_pdf(self):
        pptx = self.root / "current.pptx"
        pptx.write_bytes(b"not a package")
        stale = self.out / "current.pdf"
        stale.write_bytes(b"old pdf")
        with patch.object(check, "find_office", return_value="office"), patch.object(
                check, "_run_tool", side_effect=subprocess.CalledProcessError(1, "office")):
            pictures, problem = check.pptx_pictures(str(pptx), str(self.out), "current")
        self.assertEqual(pictures, [])
        self.assertTrue(problem)
        self.assertEqual(stale.read_bytes(), b"old pdf")

    def test_timeout_is_reported_without_aborting_other_files(self):
        with patch.object(check, "find_browser", return_value="browser"), patch.object(
                check, "BrowserSession", side_effect=subprocess.TimeoutExpired("browser", 120)), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            result = check.run([str(self.html), str(self.root / "missing.html")], str(self.out))
        self.assertEqual(result, 1)
        self.assertIn("Not checked:", output.getvalue())
        self.assertIn("does not exist", output.getvalue())

    def test_paths_are_encoded_and_only_fresh_images_are_returned(self):
        commands = []

        def browser(url, out, width, height, **kwargs):
            commands.append(url)
            Path(out).write_bytes(b"fresh picture")

        with patch.object(check, "find_browser", return_value="browser"), patch.object(
                check, "BrowserSession") as session:
            session.return_value.__enter__.return_value.shoot.side_effect = browser
            pictures, problem = check.html_pictures(str(self.html), str(self.out), "current")
        self.assertIsNone(problem)
        self.assertEqual(len(pictures), 1)
        self.assertEqual(Path(pictures[0]).read_bytes(), b"fresh picture")
        self.assertIn("%23", commands[0])
        self.assertIn("%22", commands[0])
        self.assertTrue(commands[0].endswith("#1"))

    def test_page_pictures_use_real_viewports_and_fresh_full_pages(self):
        self.html.write_text('<section class="block hero">Current content</section>')
        viewports = []

        def shoot(url, out, width, height, full_page=False):
            viewports.append((width, height, full_page))
            Path(out).write_bytes(b"fresh page")

        with patch.object(check, "find_browser", return_value="browser"), patch.object(
                check, "BrowserSession") as session:
            session.return_value.__enter__.return_value.shoot.side_effect = shoot
            pictures, problem = check.html_pictures(str(self.html), str(self.out), "current")
        self.assertIsNone(problem)
        self.assertEqual(len(pictures), 2)
        self.assertEqual(viewports, [(1280, 900, True), (390, 900, True)])

    def test_bracketed_powerpoint_name_has_fresh_pictures(self):
        pptx = self.root / "deck[1].pptx"
        pptx.write_bytes(b"not a package")

        def tool(cmd, timeout):
            if "--convert-to" in cmd:
                folder = Path(cmd[cmd.index("--outdir") + 1])
                (folder / "deck[1].pdf").write_bytes(b"fresh pdf")
            else:
                Path(cmd[-1] + "-1.png").write_bytes(b"fresh slide")

        with patch.object(check, "find_office", return_value="office"), patch.object(
                check.shutil, "which", return_value="pdftoppm"), patch.object(check, "_run_tool", side_effect=tool):
            pictures, problem = check.pptx_pictures(str(pptx), str(self.out), "deck[1]")
        self.assertIsNone(problem)
        self.assertEqual([Path(x).name for x in pictures], ["deck[1]-1.png"])

    @unittest.skipIf(os.name == "nt", "POSIX owned-process-group cleanup")
    def test_timeout_stops_only_the_started_process_tree(self):
        marker = str(self.root / "child-survived")
        child = "import pathlib,time; time.sleep(1); pathlib.Path(" + repr(marker) + ").touch()"
        parent = "import subprocess,sys,time; subprocess.Popen([sys.executable,'-c'," + repr(child) + "]); time.sleep(30)"
        with self.assertRaises(subprocess.TimeoutExpired):
            check._run_tool([sys.executable, "-c", parent], 0.3)
        time.sleep(1.1)
        self.assertFalse(Path(marker).exists(), "a descendant survived its render timeout")

    def test_tool_nonzero_exit_is_an_error(self):
        with self.assertRaises(subprocess.CalledProcessError):
            check._run_tool([sys.executable, "-c", "raise SystemExit(3)"], 10)


if __name__ == "__main__":
    unittest.main()
