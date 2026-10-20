"""Estimate how much room text needs, and shrink it until it fits its box.

The estimate uses each font's average width (design.json "width", in ems) and a
rough width per kind of character. It is deliberately a little generous; the check
pictures catch what it misses.
"""
import unicodedata

NARROW = set("iljtfrI.,;:'!|()[] ")
WIDE = set("mwMW@%")


def char_width(ch):
    """Width of one character relative to an average character (1.0)."""
    if ch in NARROW:
        return 0.55
    if ch in WIDE:
        return 1.6
    if ch.isdigit():
        return 1.1
    if ch.isupper():
        return 1.25
    if unicodedata.combining(ch):
        return 0.0
    return 1.0


def text_width(text, size, font_width, tracking=0.0):
    """Estimated width of one line of text, in the same units as size."""
    if not text:
        return 0.0
    w = sum(char_width(c) for c in text) * font_width
    return (w + tracking * len(text)) * size


def wrap(text, size, font_width, max_w, tracking=0.0):
    """Split text into lines no wider than max_w (a word longer than a line stays whole)."""
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split():
            trial = f"{line} {word}" if line else word
            if line and text_width(trial, size, font_width, tracking) > max_w:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    return lines


def fit(text, size, font_width, max_w, max_h, leading, tracking=0.0, min_scale=0.5, max_lines=None):
    """Largest size (down to size * min_scale) at which text fits max_w x max_h.

    Returns (size, lines, fits). When nothing fits, the smallest size is returned
    with fits=False so the caller can report it.
    """
    s = size
    floor = size * min_scale
    while True:
        lines = wrap(text, s, font_width, max_w, tracking)
        too_wide = any(text_width(l, s, font_width, tracking) > max_w * 1.02 for l in lines)
        too_many = max_lines is not None and len(lines) > max_lines
        if not too_wide and not too_many and len(lines) * s * leading <= max_h + 1e-6:
            return s, lines, True
        if s <= floor:
            return s, lines, False
        s = max(floor, s * 0.94)
