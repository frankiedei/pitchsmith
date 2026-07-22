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


def dewatermark(text: str) -> str:
    """Always-on backstop for the one AI tell we can fix deterministically without
    risking meaning: em/en dashes. The model is told not to use them, but it slips,
    so this runs on EVERY pitch (after the LLM audit too). Newlines are preserved.

    An em dash becomes a comma (the safe general join); an en dash between digits
    (a date/number range like 10/5–10/22) becomes a hyphen, otherwise a comma."""
    # en dash inside a numeric range -> hyphen
    out = re.sub(r"(?<=\d)\s*–\s*(?=\d)", "-", text)
    # any remaining em/en/horizontal-bar dash, with its surrounding spaces -> ", "
    out = re.sub(r"\s*[—–―]\s*", ", ", out)
    # tidy the seams the replacement can leave, per line (keep paragraph breaks)
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.;:!?])", r"\1", out)
    out = re.sub(r",\s*,", ", ", out)
    out = re.sub(r",\s*([.!?])", r"\1", out)
    return out


def strip_deterministic(text: str) -> tuple[str, list[str]]:
    """No-key fallback: remove flagged phrases, strip dashes, tidy the seams. Not
    as good as the LLM rewrite, but it guarantees the banned list and em dashes
    never ship. Returns the cleaned text and the phrases that were removed."""
    removed: list[str] = []
    out = text
    for phrase in BANNED_PHRASES:
        pattern = re.compile(re.escape(phrase), re.IGNORECASE)
        if pattern.search(out):
            removed.append(phrase)
            out = pattern.sub("", out)
    out = dewatermark(out)
    # collapse the double spaces / dangling punctuation left behind
    out = re.sub(r"[ \t]{2,}", " ", out)
    out = re.sub(r"\s+([,.;:])", r"\1", out)
    out = re.sub(r"([,;:])\1+", r"\1", out)
    return out.strip(), removed
