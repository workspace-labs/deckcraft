# Fixing a plain deck or page

The person's words are theirs. deckcraft changes the look, never the content.

1. Read their file into a draft:

   ```bash
   python3 <skill folder>/scripts/deckcraft.py extract their.pptx --out content.json
   ```

   It works for .pptx and .html. It copies every title and paragraph in order, guesses a slide type for
   each slide (title, points, section, closing), and lists what it could not carry: tables (with their
   first cells), pictures, charts. Tell the person about each of those; never drop them silently.
2. Improve the slide types, not the words. A slide of figures can become `numbers` ("Building: AED 4.2
   million" becomes value "AED 4.2 million", label "Building"); a simple bar chart can become `chart` with
   the exact values. Split a slide rather than cut it. Add `"org"` if you know it.
3. Prove no word was lost:

   ```bash
   python3 <skill folder>/scripts/deckcraft.py same-words their.pptx content.json
   ```

   It must say "Every word of the original is in the content file." It compares word occurrence
   counts, ignoring letter case and sentence-ending punctuation, while retaining Arabic diacritics
   and punctuation inside numbers. Also compare the original wording and order directly: matching
   counts cannot prove unchanged order, capitalization, or meaning. Review every notice about objects
   that could not be carried, including tables, pictures, charts and speaker notes.
4. A text longer than a slide holds is reported by `extract` or `make`. Ask the person how to shorten it;
   do not shorten it yourself.
5. Text you think could be better goes in a "Suggested changes" list in the hand-over. Change it only
   when they say yes, then run `same-words` knowing that word will now be listed.
