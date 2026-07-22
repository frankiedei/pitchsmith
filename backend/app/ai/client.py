"""Thin Anthropic SDK wrapper — inherited from the Label OS backend.

Everything AI degrades gracefully when no key is set: the deterministic layers
(anti-AI phrase audit, fact extraction fallbacks) still run. Kept deliberately
close to the parent's ai/client.py so the two can be merged later.
"""
import json
import logging
import re

from ..config import settings

log = logging.getLogger("pitchsmith.ai")

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None


def available() -> bool:
    return bool(settings.anthropic_api_key) and anthropic is not None


def _client():
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def complete(prompt: str, *, model: str, system: str = "",
             max_tokens: int = 2000, temperature: float | None = None) -> str:
    kwargs: dict = dict(
        model=model,
        max_tokens=max_tokens,
        system=system or anthropic.NOT_GIVEN,
        messages=[{"role": "user", "content": prompt}],
    )
    if temperature is not None:
        kwargs["temperature"] = temperature
    msg = _client().messages.create(**kwargs)
    return "".join(b.text for b in msg.content if b.type == "text")


_json_re = re.compile(r"```(?:json)?\s*([\s\S]*?)```")


def complete_json(prompt: str, *, model: str, system: str = "", max_tokens: int = 3000):
    """Ask for JSON, tolerate code fences / stray prose. Returns None on failure
    so callers can hold state instead of crashing (parent's convention)."""
    raw = complete(prompt, model=model, system=system, max_tokens=max_tokens)
    m = _json_re.search(raw)
    if m:
        raw = m.group(1)
    for opener, closer in (("[", "]"), ("{", "}")):
        if opener in raw:
            sliced = raw[raw.index(opener): raw.rindex(closer) + 1]
            try:
                return json.loads(sliced)
            except json.JSONDecodeError:
                continue
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("AI returned non-JSON output; skipping. Head: %r", raw[:200])
        return None
