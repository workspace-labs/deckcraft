# deckcraft scope

## What it does

An agent skill. Someone brings a brief, or a plain PowerPoint or HTML page. The agent shows a library of
12 ready-made designs, the person picks one, and the agent makes a PowerPoint, a web page, HTML slides, or
any mix of them, in that design, in English or Arabic. Every page is checked in a picture before
hand-over, and the person can ask for changes until they say done.

## What it will not do

- Change the 12 approved designs. A brand named in the brief only adds its accent colour and logo on top.
- Invent facts, numbers, quotes or sources. Missing content is asked for, never made up.
- Rewrite someone's words when fixing their file. Text fixes are suggested, and made only on a yes.
- Hand over a file that was not checked page by page.
- Need anything installed to make files. Python 3.9+ alone writes all three outputs; Chrome and
  LibreOffice are only used to take the check pictures.
- Reach the network while making files. (A web page links Google Fonts for its look when it is opened;
  plain fonts take over offline.)

## How good it must be

- Every slide and page looks like the approved preview of its design.
- Arabic reads right to left, with the whole layout mirrored, in all 12 designs and all 3 outputs.
- A .pptx opens in Microsoft PowerPoint (Mac and Windows), Keynote and LibreOffice without a repair prompt.
- Text that does not fit is shrunk to fit or reported; it never runs off a slide silently.
- Works the same in Claude Code, Codex and other agents, on Mac and Windows.
