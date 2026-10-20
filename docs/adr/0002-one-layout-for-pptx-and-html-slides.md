# ADR 0002: one slide layout drives both the PowerPoint and the HTML slides

Date: 2026-10-21 · Status: accepted

## Context

The person can ask for a PowerPoint and HTML slides of the same deck. If each were laid out separately
they would drift apart, and Arabic would have to be mirrored twice.

## Decision

A layout engine (`deckcraft/layout.py`) places every element of every slide in one coordinate system:
1 unit = 1% of the slide width (a 16:9 slide is 100 × 56.25 units). It returns plain shapes, texts and
images. The PowerPoint writer and the HTML slides writer only draw that list. Arabic is the same layout
mirrored left to right.

## Consequences

- PowerPoint and HTML slides of one deck match.
- Text sizes are chosen by the engine to fit their box (an estimate from each font's average width), so
  both outputs get the same size. The check pictures catch what the estimate misses.
- The web page is different by nature (it scrolls) and uses its own CSS, from the same colours and fonts.
