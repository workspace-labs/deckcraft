# ADR 0001: write the PowerPoint file directly

Date: 2026-10-21 · Status: accepted

## Context

deckcraft must make real .pptx files on any computer an agent runs on, in English and Arabic, and
later embed the design's fonts (the owner's pick). The usual library, python-pptx, is not installed on
the owner's Mac and would have to be installed everywhere. It also has no support for embedding fonts,
and right-to-left text needs raw XML through it anyway.

## Decision

Write the .pptx with the Python standard library only: a .pptx is a zip of XML files. deckcraft writes the
smallest valid package itself (one master, one blank layout, one slide per content slide) and draws
every element as a positioned shape.

## Consequences

- Nothing to install; works on Mac, Windows and Linux with Python 3.9+.
- Full control of right to left (`rtl="1"`), Arabic fonts (`<a:cs>`) and, in phase 2, embedded fonts.
- deckcraft owns the XML: every package is checked by tests (parts listed, XML well formed) and opened
  in real PowerPoint before a release.
- Slides are built from positioned shapes, not editable placeholders, so a person editing the deck later
  moves boxes rather than typing into layouts. Accepted: the deck is delivered finished.

## Changed from the owner's folder picture

The approved folder picture showed a `layouts.pptx` in each design folder. Because the PowerPoint is drawn
from `design.json`, that file is not needed: the PowerPoint look lives in `design.json`, beside the web
look in `style.css`. Twelve binary templates would also drift from the web look over time.
