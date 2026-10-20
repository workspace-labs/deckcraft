# Changelog

All notable changes to deckcraft. The version is `VERSION` in `skills/deckcraft/deckcraft/__init__.py`.

## [0.1.0] - 2026-10-21

The first version. Not yet independently reviewed.

### Added

- The 12 approved designs as folders (`design.json` + `style.css`) and the picker page.
- One JSON content file with seven slide types; plain numbered reasons for anything wrong.
- A slide layout engine shared by the PowerPoint and the HTML slides; text sized to fit using each
  font's measured width; Arabic laid out as the mirror image.
- PowerPoint writer using only the Python standard library; opened and exported by Microsoft
  PowerPoint for Mac and LibreOffice in testing.
- HTML slides (keyboard, full screen, print) and a responsive web page, English and Arabic.
- `check`: a picture of every slide, the page on desktop and phone, and the PowerPoint via LibreOffice.
- The design's fonts travel inside the PowerPoint: 27 OFL families (72 static files) bundled, each
  deck embeds the ones it uses as EOT, which PowerPoint for Mac draws without the fonts installed.
  `--fonts safe` embeds nothing. The check gives LibreOffice the same fonts.
- `extract` reads an existing .pptx or .html (tested on a deck made by PowerPoint for Mac) into a draft
  content file with every word, and lists tables, pictures and charts it cannot carry.
- `same-words` proves the content file kept every word of the original.
- 38 tests.
