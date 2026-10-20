---
name: deckcraft
description: Makes presentations and web pages with real design. Someone brings a brief (or a plain PowerPoint or HTML page), picks one of 12 ready-made designs, and gets a PowerPoint (.pptx), HTML slides, a web page, or any mix, in the same look, in English or Arabic, checked slide by slide before hand-over. Use when someone asks for a deck, slides, a presentation, a pitch deck, a PowerPoint, a one-page website or landing page from a brief, or says their deck or page looks plain and wants it redesigned. Not for documents, reports or spreadsheets, charts on their own, or a full multi-page website or app.
---

# deckcraft

Twelve approved designs, one content file, three outputs. The design is already done and tested,
so the work is: understand the request, let the person pick a look, write their words into the
content file, make the files, look at every page, hand over.

Everything runs with Python 3.9+ and nothing else installed:

```bash
python3 <skill folder>/scripts/deckcraft.py designs                 # list the 12 designs
python3 <skill folder>/scripts/deckcraft.py picker                  # path of the picker page
python3 <skill folder>/scripts/deckcraft.py make content.json --design 3 --formats pptx,slides,page --out out
python3 <skill folder>/scripts/deckcraft.py check out/*.pptx out/*.html
python3 <skill folder>/scripts/deckcraft.py extract their.pptx --out content.json   # fixing a deck
python3 <skill folder>/scripts/deckcraft.py same-words their.pptx content.json      # no word lost
```

## 1. Understand the request

- **A new deck or page from a brief.** You need: the topic, who will see it, the key points with
  their real numbers and names, about how many slides, the language (English or Arabic), and which
  outputs (PowerPoint, HTML slides, web page). If the brief is too thin for that, **ask one short round
  of questions** first. Offer choices where your tool can. Never fill a gap with invented facts,
  numbers, quotes or sources.
- **Fixing a plain deck or page someone already made.** Their words stay exactly as they are; only the
  look changes. `deckcraft.py extract their.pptx --out content.json` copies every word into a draft
  and lists what it cannot carry (tables, pictures, charts). Before making, `deckcraft.py same-words
  their.pptx content.json` must say every word is there. Suggest text changes; make them only on
  their yes. Read `references/fixing.md`.
- Confirm the outputs and language in one line before making anything.

## 2. Let them pick a design

Show the picker page (`deckcraft.py picker` prints its path; open it or send it). Every design is
shown as an English slide and an Arabic web page. Ask for the number.

| # | Design | Good for |
|---|---|---|
| 01 | Modern Gradient | Modern business, product launches, apps |
| 02 | Bold Editorial | Stories, launches, announcements |
| 03 | Nature & Earth | Sustainability, health, food, real estate |
| 04 | Minimal Swiss | Portfolios, design talks |
| 05 | Government Formal | Ministries, official briefs |
| 06 | Warm Friendly | Education, community, health |
| 07 | Data Focus | Results, KPIs, finance |
| 08 | Luxury | Premium brands, events, galas |
| 09 | Gulf Heritage | UAE and Gulf audiences |
| 10 | Playful Pop | Youth, marketing, social |
| 11 | Academic | University, research, theses |
| 12 | Pitch Deck | Investors, competitions |

If they cannot see the page, describe two or three that fit their brief and recommend one.
**A brand** named in the brief adds its accent colour and logo on top (`"brand"` in the content
file). The 12 designs themselves are never changed.

## 3. Write the content file

One JSON file holds the words; the same file makes all three outputs. Slide types: `title`,
`section`, `points`, `numbers`, `chart`, `quote`, `closing`. The full format, limits and an example are
in `references/content-format.md`; complete files are in `examples/`.

- Keep slides short: a title and 2 to 6 points, or 2 to 4 numbers. Split long content across slides.
- Numbers, names, dates and quotes come from the person or their file, never from you.
- Arabic: set `"lang": "ar"` and write the Arabic text; the whole layout mirrors right to left.

## 4. Make the files

```bash
python3 <skill folder>/scripts/deckcraft.py make content.json --design <number> --formats pptx,slides,page --out <folder>
```

- If it refuses, it lists numbered reasons. Fix exactly those in the content file and run again.
- If it prints "Look at these before handing over", a text was too long for its slide: shorten it
  (with the person's yes, if it is their text) or split the slide, and make again.
- The PowerPoint carries the design's fonts inside it, so it looks right on any computer with
  PowerPoint. `--fonts safe` uses plain fonts (Arial, Georgia) instead: choose it when the deck will be
  opened in Keynote or Google Slides, or must stay small.

## 5. Look at every page

```bash
python3 <skill folder>/scripts/deckcraft.py check <the made files>
```

It saves a picture of every slide, the web page on a desktop and on a phone, and the PowerPoint as
LibreOffice draws it. **Open and look at every picture.** Look for text cut off or running into other
text, text over a shape, Arabic letters broken apart, an empty slide, and anything unlike the chosen
design. Fix the content and make again until every page is clean.

If the check cannot run (no Chrome/Edge or no LibreOffice), say so plainly in the hand-over: say
which files were not checked, and ask the person to open them. Never call an unchecked file checked.

## 6. Hand over, then change rounds

Give the file paths, the design, and what you checked. List any suggested text changes (never made
without their yes). Then ask if they want changes. They can change words, slides, or switch to
another design (same content file, another `--design`). Make, check and hand over again, as many
rounds as they want, until they say done.

## Never

- Never change the 12 designs, their colours or their fonts.
- Never invent facts, numbers, quotes, names or sources.
- Never rewrite someone's own text without their yes.
- Never hand over a file whose pages you did not look at, without saying so.

## Limits

- Slide types are the seven above; a slide holds at most 6 points or 4 numbers; a deck up to 40 slides.
- Fonts: the PowerPoint carries its fonts (proven in PowerPoint for Mac; not yet tried in PowerPoint for
  Windows, Keynote or Google Slides). HTML outputs load the fonts from Google Fonts when online and use
  plain fonts offline.
- Pictures and logos: PNG or JPEG.
