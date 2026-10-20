"""Shared test setup: put the skill on the import path and find the examples."""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "deckcraft")
EXAMPLES = os.path.join(SKILL, "examples")
sys.path.insert(0, SKILL)


def example(lang="en"):
    with open(os.path.join(EXAMPLES, f"northwind-{lang}.json"), encoding="utf-8") as f:
        return json.load(f)
