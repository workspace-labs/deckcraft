# Deckcraft test evidence

## 0.1.3 — 2026-10-21

The user requested testing and repair of the linked skill, then explicitly authorized commit and
push. Baseline: clean `main` at `b8cb138003ed2b9ba65ac356dfada1724ddd19e9` (0.1.2). The original
81-test suite passed before implementation changes, with real Chrome enabled outside the execution
sandbox; the first sandboxed attempt could not start Chrome and is not counted as a passing run.

### Final automated result

**108 tests passed, 0 failed, 0 skipped**, including **3 real Chrome integration tests**. The 27 new
tests comprise 5 HTML extraction tests, 7 chart tests, 9 image tests, 1 numbered-slide capture test,
and 5 LibreOffice input-isolation tests. Subcases and focused runs are not added to the 108.

```bash
DECKCRAFT_BROWSER_TESTS=1 PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests
```

Without `DECKCRAFT_BROWSER_TESTS=1` and Chrome on macOS, the ordinary suite skips the three real-browser
tests. Those skipped runs do not establish real rendering correctness.

### What was wrong and what changed

- `extract.py`: adjacent/nested block elements joined visible words. Semantic block boundaries now
  separate them, while inline markup still preserves words such as `Inter<strong>national</strong>`.
- `content.py`, `layout.py`, `html_page.py`: multiplication before normalization overflowed on accepted
  finite values near `1e308`; integers beyond the finite numeric range crashed. Ratios are now formed
  first and unsupported magnitudes become numbered content errors. Shared automatic labels preserve
  supplied decimals: `1.25` and `0.005` previously became `1.2` and `0.0`.
- `images.py`, `html_page.py`: truncated headers and zero dimensions could abort generation or embed
  unusable logos in the page. They now produce warnings and omit the unusable logo in every output;
  valid JPEG marker padding remains accepted.
- `check_browser.py`: a reload could cancel an asynchronous fragment navigation and capture the
  preceding slide. The checker waits for the requested URL on the correct frame before reloading.
  The real test covers sequential, repeated and out-of-order requests and checks actual PNG colors
  as well as the active slide and URL.
- `check.py`: LibreOffice's older bundled Rubik Bold could override the embedded Arabic-capable font,
  leaving Arabic titles blank. Only its disposable rendering input receives unique font-name
  attributes. The delivered PowerPoint, visible words, namespace prefixes and font binaries stay intact.

Each repair family has a recorded failing regression before its correction and a passing run after.
A read-only reviewer checked the implementation and exercised the new tests. The reviewer supplied
part of the screenshot regression oracle, so that oracle is shared authorship rather than independent
acceptance. A separate worker implemented the font-copy helper; the main agent and read-only reviewer
checked it. The reviewer also compared all 24 actual decks: source hashes and embedded font bytes
were unchanged, and XML differed only in the intended temporary font-name attributes.

### Rendering and package checks

- Made all **24 example decks**: 12 designs × English/Arabic, with all three formats (**72 files**).
- Captured **168 HTML slide pictures**, **48 desktop/phone page pictures**, and **168 LibreOffice
  slide pictures**: **384 example views**, inspected through contact sheets. All PowerPoint pictures
  were regenerated with the final font-isolation repair; the missing Nature & Earth Arabic titles
  are visibly restored. One page check failed during the parallel run, reported failure correctly,
  and passed a separately logged fresh retry.
- Rendered before/after decimal-chart fixtures in English and Arabic: **16 additional pictures**
  across PowerPoint, HTML slides and desktop/phone pages; the label precision correction is visible.
- Packed the final skill's **150 files**, unpacked it into an isolated directory containing spaces,
  and ran **4 builds producing 12 outputs** with `python3 -I -S -B`: English/Arabic and safe/design
  fonts. All passed without third-party Python packages or a skill installation.
- Static skill audit: **0 structural errors**, the same **2 process-launch review notices** as before,
  no new findings, with finite limits of 320 files / 1 MiB per file / 20 MiB total. Process ownership,
  timeouts and cleanup are covered by the inspected checker paths and regression tests.
- Compared **128 approved design, font and media files** against the backed-up baseline: unchanged.
  No dependency, design identity, font asset, installation or delivered-file format was changed.
- `git diff --check` passed. A complete source backup and before/after digests were retained outside
  the repository; generated decks, pictures and verification logs were also kept outside the skill.

Environment: macOS 27.0.1, Python 3.9.6, Chrome 155.0.8059.85, LibreOffice 26.8.0.3.

### Limits of this verification

No fresh native PowerPoint GUI, Windows, Linux, Keynote, Google Slides, Safari or Firefox run was
performed in this repair pass. LibreOffice and Chrome rendering support the tested repairs; they do
not prove universal viewer compatibility. Every new final deck/page still needs its own inspection.
No runtime dependency was added and no installed skill mirror was changed.

---

## Previous review — 0.1.2

Date: 2026-10-21. Tested version: **0.1.2**. Review started from clean commit
`b8d22c076a696f13cefe97c7fd118be7be8cec60` (0.1.1).

### Final result

**81 automated tests passed, 0 failed, 0 skipped.** The original suite had 38 tests;
this review added 43 tests. Focused runs below are subsets and are not added to the 81.

The final suite included **2 real Chrome integration tests**: normal desktop/phone viewport
capture and capture after animations settle. An independent follow-up ran the **23 checker tests**,
including both real browser tests: all passed, with no skips.

Final command, run from the repository root:

```bash
DECKCRAFT_BROWSER_TESTS=1 PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest discover -s tests
```

Environment: macOS 27.0.1, Python 3.9.6, Chrome 155.0.8059.85, LibreOffice 26.8.0.3.
The real-browser tests are opt-in and currently target Chrome on macOS. Without the environment
flag, the ordinary suite skips those 2 tests and must not be reported as having run them.

### What the automated tests checked

- JSON rules, all errors reported together, wrong slide types, unknown fields and field limits.
- Rejection of NaN/infinity and characters that would make invalid PowerPoint XML.
- All 12 designs load, colours resolve, requested font weights exist and every used HTML font
  weight/italic variant is requested.
- Layout boundaries, text-box collisions, right-to-left mirroring and long-content warnings.
- Long Pitch Deck number rows and Arabic-Indic/Eastern Arabic figures.
- PowerPoint XML well-formedness, package relationships, safe fonts, embedded fonts and EOT headers.
- HTML/XML escaping and making all 3 output formats from the command line.
- Extraction from a PowerPoint-made fixture and HTML; preserving paragraphs, line-break boundaries,
  repeated words, Arabic diacritics and punctuation inside numbers.
- Separate table/picture notices, nested or unmatched HTML table tags, and notices for speaker notes.
- Failed renders never accepted as old screenshots/PDFs; encoded file URLs, bracketed filenames,
  separate evidence for same-named inputs and output names confined to the chosen folder.
- Renderer nonzero exits and timeouts; owned POSIX child-process cleanup.
- Local-only browser protocol validation, bounded responses, phone viewport width, full-page
  capture without stretching viewport-height layouts, and settled finite/infinite animations.

### Rendering and visual inspection

- **24 example decks:** 12 designs × English/Arabic.
- **168 slide pictures:** 24 decks × 7 slide types.
- **48 full-page pictures:** 24 web pages × desktop/phone.
- **216 example views in total**, inspected through contact sheets by the reviewing agents.
  No concrete clipping, text collision or broken Arabic shaping was observed in these examples.
  Loaded-font measurements also found no horizontal text overflow in those views.
- **48 maximum-content slides** exercised valid-limit titles, points and figures across all
  design/language combinations. The independent measurement sweep used all 72 bundled font faces.
  Silent boundary failures fell from 12 to 0; content that still could not fit produced a warning.
- **1 end-to-end Arabic design 09 run:** 3 output files made, then the real checker produced
  **16 fresh pictures**: 7 HTML slides, 7 LibreOffice-rendered PowerPoint slides, 2 web-page views.
  This is a separate execution, not 16 extra unique example cases.
- **1 viewport regression:** the previous tall screenshot window stretched an 80vh hero to
  4,800 pixels. The repaired checker kept a 900-pixel viewport, a 720-pixel hero and a 2,320-pixel
  full-page image. The phone image was genuinely 390 pixels wide.
- **1 actual-deck animation reproduction:** a screenshot initially captured the entry fade at
  opacity 0.640295. The independent follow-up captured opacity 1 with no running entry animation.

Visual checks used local bundled fonts and blocked browser network access. This proves those
local-font renderings; it does not prove every online/offline fallback combination on every browser.

### Additional independent format checks

- **72 bundled font files** checked field by field against the EOT 2.1 structure, including
  byte-for-byte recovery of the original font data.
- **360 PowerPoint XML parts** from all 24 decks validated against the official ECMA transitional
  schemas. This covers relevant presentation, drawing and extended-properties parts; it is not a
  claim that every package component received full semantic validation.
- **12 Google Fonts requests** returned HTTP 200 after correcting missing variant requests.
- **127 protected design/font/original-picture files** compared with the before-image: unchanged.
- Static skill audit: **0 structural errors** with a finite 20 MiB scan bound, sufficient for the
  bundled fonts. It retained **2 execution-primitive review notices** for the checker modules;
  their process-launch and cleanup paths were manually reviewed and exercised.
- `git diff --check` passed. The supplied README picture was copied byte for byte to
  `media/deckcraft-hero-0.1.2.png`; the fresh filename avoids a stale image URL.

### What remains untested

- Native PowerPoint on Windows, Keynote, Google Slides, Safari and Firefox.
- Native Windows process-tree cleanup and Windows/Linux runtime behaviour.
- A fresh skill installation in another agent, or a clean computer without the review environment.
- A fresh Microsoft PowerPoint GUI run during this review. Earlier Mac PDF/font evidence was
  inspected, and this review rendered the sample with LibreOffice.

Passing these checks supports the repairs described in `CHANGELOG.md`; it does not establish
universal application compatibility or guarantee that arbitrary content will fit. Every final
deck/page still needs its own page-by-page visual inspection. `same-words` checks occurrence counts;
direct review is still needed for order, punctuation, capitalization and meaning.
