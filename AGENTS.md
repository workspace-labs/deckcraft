# AGENTS.md: working on deckcraft

For coding agents changing this repository. What the skill does is in `README.md`; what it must never do
is in `docs/scope.md`; why it is built this way is in `docs/adr/`; what is left is in `docs/plan.md`.

## Test

```bash
python3 -m unittest discover -s tests
```

Python 3.9 or newer, standard library only. Keep it that way: the skill must run on a stranger's clean
computer with nothing installed.

## Look at the slides

Tests check the numbers, not the look. After any change to a design or the layout, make both examples
with every design you touched and look at every `check` picture:

```bash
cd skills/deckcraft
python3 scripts/deckcraft.py make examples/northwind-ar.json --design 9 --out /tmp/dc
python3 scripts/deckcraft.py check /tmp/dc/*
```

## Rules for this repository

- Keep `skills/deckcraft/` clean: it is installed as it is. No tests, no made files.
- The 12 designs are the owner's approved look. Never change their colours, fonts or shapes without his
  yes. `designs/picker.html` is the approved picture of them.
- `layout.py` decides where everything goes; the writers (`pptx/`, `html_slides.py`) only draw. Arabic is
  handled once, by mirroring in `layout.py`.
- Every change bumps `VERSION` in `skills/deckcraft/deckcraft/__init__.py` and adds a dated
  `CHANGELOG.md` entry.
- Never commit or push without the owner's word. Never put a path from the owner's computer in anything
  published.
