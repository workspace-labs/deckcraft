# Changelog

All notable changes to deckcraft. The version is `VERSION` in `skills/deckcraft/deckcraft/__init__.py`.

## [0.1.3] - 2026-10-21

### Fixed

- Keep visible words separate when extracting adjacent or nested HTML block elements, while
  preserving words joined by inline markup.
- Scale chart ratios before multiplying so large finite values cannot produce infinite coordinates;
  report integers outside the finite numeric range as content errors.
- Preserve the supplied precision in automatic chart labels in PowerPoint, HTML slides and web pages.
- Report truncated logo headers and zero image dimensions as warnings, omit unusable logos consistently
  from slides and web pages, continue making the requested files, and retain valid JPEG marker padding.
- Wait for a numbered slide's fragment navigation to commit before reloading for a check picture,
  so screenshots cannot silently repeat the preceding slide.
- Isolate embedded font names in a disposable LibreOffice render copy, preventing its older bundled
  Rubik Bold from hiding Arabic text; leave the delivered PowerPoint and bundled font files unchanged.
- Add regression tests for these input boundaries and record the fresh verification in `test-evedince.md`.

## [0.1.2] - 2026-10-21

### Fixed

- Preserve both closing paragraphs, HTML line-break word boundaries, repeated-word counts, and
  separate table/picture notices when restyling a file; report attached speaker notes as uncarried.
- Refuse malformed slide types, nonfinite chart values and characters that would break PowerPoint XML.
- Keep long Pitch Deck number rows on the slide and size Arabic-Indic figures conservatively.
- Request all HTML font weights and italics actually used; keep Arabic page text upright like the slides.
- Require fresh successful check renders, encode local file URLs, preserve separate evidence for
  same-named inputs, handle bracketed filenames, and stop only the renderer's own process tree on timeout.
- Capture full web pages at normal desktop and true 390-pixel phone viewports, with fonts ready, so
  viewport-height spacing is not stretched by the screenshot window.
- Restrict output names to filenames so they cannot write outside the selected output folder.
- Clarify that word counts supplement direct text review and that unchecked drafts are not final deliveries.
- Point the README at the owner's supplied picture using a fresh versioned image URL to avoid stale previews.
- Record the review's 81 passing tests, rendering counts and remaining platform limits in `test-evedince.md`.

## [0.1.1] - 2026-10-21

### Added

- The README picture (`media/deckcraft-hero.png`): the twelve designs as a hand of cards, the owner's
  pick (option D of seven).

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
