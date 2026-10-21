# ADR 0003: the design's fonts travel inside the PowerPoint, as EOT

Date: 2026-10-21 · Status: accepted

## Context

The owner chose: "embed the real fonts, plain fonts as backup". A .pptx names its fonts; a computer
without them shows a substitute (Calibri on the Mac), and the design is lost.

## What was tried (PowerPoint for Mac, fonts not installed)

- The font file stored as plain TTF in `ppt/fonts/*.fntdata`: PowerPoint ignored it and drew Calibri.
- The same font wrapped as Embedded OpenType 2.1 (uncompressed): PowerPoint drew the real font. `pdffonts`
  on PowerPoint's own PDF export listed only the embedded fonts, for English and Arabic decks.

## Decision

- Bundle the static TTF of every (family, weight, slant) the 12 designs use, from Google Fonts, with each
  family's OFL licence: `skills/deckcraft/fonts/` (made by `tools/fetch_fonts.py`; 72 files, about 11 MB).
- A text in the PowerPoint names the exact font inside the file (Manrope at 800 is "Manrope ExtraBold";
  at 700 it is "Manrope" with bold on), so the name always matches what is embedded.
- Embed only the fonts a deck uses, each as EOT, listed in `embeddedFontLst`.
- `--fonts safe` keeps the old way: plain fonts every computer has, nothing embedded.
- The check gives LibreOffice the same files. Since 0.1.3 it also uses private font-name aliases in a
  temporary render copy: current LibreOffice can read embedded EOT, but an older same-name bundled
  font can override it. The aliases avoid that collision without changing the delivered deck or fonts.

## Consequences

- A deck looks like its design on any computer with PowerPoint; a deck grows by about 100 to 400 KB per
  font it carries.
- The fonts are not changed (OFL: no renaming), so the bold/regular grouping follows each file's own names.
- Still to prove: PowerPoint for Windows, Keynote and Google Slides (they may fall back to plain fonts;
  the design's fallback fonts are the safe choice for those).
- The skill folder is about 11 MB bigger.
