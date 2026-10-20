#!/usr/bin/env python3
"""Run deckcraft: python3 scripts/deckcraft.py <command> ... (see SKILL.md)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if sys.version_info < (3, 9):
    sys.exit("deckcraft needs Python 3.9 or newer.")

from deckcraft.cli import main  # noqa: E402

sys.exit(main())
