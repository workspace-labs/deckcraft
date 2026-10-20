# deckcraft

An agent skill that makes presentations and web pages with real design.

Someone brings a brief, or a plain PowerPoint or HTML page. The agent shows **12 ready-made designs**,
the person picks one, and the agent makes a **PowerPoint (.pptx)**, **HTML slides**, a **web page**, or
any mix, all in the same look, in **English or Arabic**. Every slide and page is checked in a picture
before hand-over, and the person can ask for changes until they say done.

Works in Claude Code, Codex and other agents that read `SKILL.md`. Needs **Python 3.9+ and nothing else**
to make files.

## The 12 designs

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

Open `skills/deckcraft/designs/picker.html` to see them all.

## Install

The skill needs Python 3.9 or newer and nothing else.

**Claude Code, Codex and other agents**, in one line:

```bash
npx skills add workspace-labs/deckcraft -g
```

Or by hand, for Claude Code:

```bash
git clone https://github.com/workspace-labs/deckcraft.git
mkdir -p ~/.claude/skills
cp -R deckcraft/skills/deckcraft ~/.claude/skills/
```

**Claude app (chat and Cowork)**: make the zip, then upload it in **Customize → Skills**.

```bash
cd deckcraft
mkdir -p dist
(cd skills && zip -r -X ../dist/deckcraft.zip deckcraft -x '*.DS_Store' -x '*__pycache__*')
```

For the check pictures, install Chrome (or Edge) and LibreOffice; without them the skill still makes every
file and says plainly which pictures it could not take.

## Try it

```bash
cd skills/deckcraft
python3 scripts/deckcraft.py designs
python3 scripts/deckcraft.py make examples/northwind-en.json --design 3 --out out
python3 scripts/deckcraft.py check out/northwind-en.pptx out/northwind-en-slides.html out/northwind-en-page.html
```

`make` writes `northwind-en.pptx`, `northwind-en-slides.html` (presents in a browser: arrow keys, F for
full screen, prints one slide per page) and `northwind-en-page.html` (a scrolling web page).
`check` saves a picture of every slide and page; it uses Chrome/Edge for HTML and LibreOffice for
PowerPoint if they are installed, and says so plainly if they are not.

The words live in one JSON content file: see `skills/deckcraft/references/content-format.md`.

## How it is built

| Part | Where |
|---|---|
| What the agent does, step by step | `skills/deckcraft/SKILL.md` |
| The 12 designs (`design.json` = colours, fonts, slide look; `style.css` = web look) | `skills/deckcraft/designs/` |
| Content file rules | `skills/deckcraft/deckcraft/content.py` |
| Slide layout for PowerPoint and HTML slides, Arabic mirrored | `skills/deckcraft/deckcraft/layout.py` |
| PowerPoint writer (standard library only) | `skills/deckcraft/deckcraft/pptx/` |
| HTML slides and web page writers | `skills/deckcraft/deckcraft/html_slides.py`, `html_page.py` |
| Check pictures | `skills/deckcraft/deckcraft/check.py` |
| Bundled fonts and how they are fetched | `skills/deckcraft/fonts/`, `tools/fetch_fonts.py` |
| Why it is built this way | `docs/adr/` |
| What it will and will not do | `docs/scope.md` |
| How it works, A to Z | `docs/workflow/` |

## Tests

```bash
python3 -m unittest discover -s tests
```

They make every design in both languages and check: content rules, nothing off the slide, no text
running into other text, Arabic mirrored, every PowerPoint package well formed with every link
resolving, and HTML escaping. They cannot see the slides: after a change to a design, make the
examples and look at the `check` pictures.

## Status

Version 0.1.0, the first version (2026-10-21). It makes new decks and pages, carries the design's fonts
inside the PowerPoint (proven in PowerPoint for Mac), and restyles an existing deck or page with every word
kept (`extract` and `same-words`). An independent review is next; fixes will come as 0.1.x. See `docs/plan.md`.

## Limits

- Seven slide types: title, section, points, numbers, chart, quote, closing.
- The PowerPoint carries its fonts (27 free OFL families, bundled in `skills/deckcraft/fonts/`, see
  `CREDITS.md`). Tried in PowerPoint for Mac; PowerPoint for Windows, Keynote and Google Slides are not
  tried yet. `--fonts safe` uses plain fonts and carries none.
- HTML outputs load fonts from Google Fonts when online; plain fonts take over offline.
