"""Deterministic anti-AI phrase audit — the guard that runs whether or not an
API key is present. Mirrors the Label OS philosophy: one AI pass wrapped in
deterministic checks. This scans for banned phrases (Stage 3 input) and, as a
last resort with no key, does a plain textual strip.
"""
import re

from ..ai.prompts import BANNED_PHRASES


def scan(text: str) -> list[str]:
    """Return the banned phrases present in `text` (case-insensitive), in order
    of first appearance. This list is handed to the LLM audit to target."""
    low = text.lower()
    hits = [(low.find(p), p) for p in BANNED_PHRASES if p in low]
    return [p for _, p in sorted(hits)]


def strip_deterministic(text: str) -> tuple[str, list[str]]:
    """No-key fallback: remove flagged cliché phrases and tidy the seams. Not as
    good as the LLM rewrite, but it guarantees the banned list never ships.
    Em dashes and colons are now allowed (the gold examples use them), so this no
    longer touches punctuation. Returns the cleaned text and phrases removed."""
    removed: list[str] = []
    out = text
    for phrase in BANNED_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(out):
            removed.append(phrase)
            out = pattern.sub("", out)
    # collapse the double spaces / dangling punctuation the phrase removal leaves
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    out = re.sub(r"([,;:])\1+", r"\1", out)
    return out.strip(), removed
