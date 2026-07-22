"""The three-stage agentic chain, in the Label OS pipeline style: one clear
orchestrator, each stage a small function, deterministic guards around the AI.

  Stage 1  classify()  — strategy classifier & fact extractor  (cheap model)
  Stage 2  generate()  — pitch generator, 2-3 variations        (quality model)
  Stage 3  audit()     — style & anti-AI audit                  (cheap model)

Every stage degrades gracefully with no API key: classify falls back to a
heuristic, generate returns a held note, audit runs deterministically.
"""
import logging
import re

from sqlalchemy.orm import Session

from ..config import settings
from ..logic import audit as audit_logic
from ..logic import feedback as feedback_logic
from .. import models
from . import client as ai
from . import prompts

log = logging.getLogger("pitchsmith.pipeline")


# --- Stage 1 --------------------------------------------------------------

def classify(context: str) -> dict:
    """Return the strategy payload. With no key, fall back to a length/quote
    heuristic so the pipeline still produces a usable archetype."""
    if not ai.available():
        return _heuristic_strategy(context)
    try:
        out = ai.complete_json(
            prompts.classifier_prompt(context),
            model=settings.ai_classify_model,
            system=prompts.CLASSIFIER_SYSTEM,
            max_tokens=1500,
        )
    except Exception:
        log.exception("classifier AI call failed; using heuristic")
        out = None
    if not isinstance(out, dict) or "archetype" not in out:
        log.warning("classifier returned unusable output; using heuristic")
        return _heuristic_strategy(context)
    # normalise the archetype to one of the two known values
    if out.get("archetype") not in (prompts.ARCHETYPE_A, prompts.ARCHETYPE_B):
        out["archetype"] = prompts.ARCHETYPE_A
    for key in ("key_anchors", "press_quotes", "cultural_themes",
                "comparison_artists", "sensory_motifs", "descriptors",
                "angle_options"):
        if not isinstance(out.get(key), list):
            out[key] = []
    out["descriptors"] = [str(d).strip() for d in out["descriptors"] if str(d).strip()]
    out["angle_options"] = [str(a).strip() for a in out["angle_options"] if str(a).strip()]
    out.setdefault("recommended_angle", "")
    if not out["recommended_angle"] and out["angle_options"]:
        out["recommended_angle"] = out["angle_options"][0]
    out.setdefault("artist_voice", "")
    return out


def suggested_style(strategy: dict) -> str:
    """Smart default for the style dropdown: an established artist with press to
    lean on gets 'authority'; everyone else gets 'match' (echo their own voice)."""
    if strategy.get("archetype") == prompts.ARCHETYPE_B and strategy.get("press_quotes"):
        return "authority"
    return "match"


def suggest_themes(context: str, existing: list[str], n: int = 6) -> list[str]:
    """The 'generate more' button: more descriptor tags grounded in the sheet,
    excluding ones already present. Empty list with no key."""
    if not ai.available() or not context.strip():
        return []
    try:
        out = ai.complete_json(
            prompts.suggest_themes_prompt(context, existing, n),
            model=settings.ai_classify_model, system=prompts.SUGGEST_SYSTEM,
            max_tokens=600,
        )
    except Exception:
        log.exception("theme suggestion AI call failed")
        return []
    if not isinstance(out, list):
        return []
    have = {e.lower() for e in existing}
    seen: set[str] = set()
    fresh: list[str] = []
    for d in out:
        tag = str(d).strip()
        low = tag.lower()
        if tag and low not in have and low not in seen:
            seen.add(low)
            fresh.append(tag)
    return fresh[:n]


def _heuristic_strategy(context: str) -> dict:
    """No-AI fallback: a quote or lots of material implies Authority (B),
    otherwise Worldbuilding (A). Honest and deterministic."""
    has_quote = '"' in context or "“" in context
    established = has_quote or len(context) > 1500
    return {
        "archetype": prompts.ARCHETYPE_B if established else prompts.ARCHETYPE_A,
        "key_anchors": [],
        "press_quotes": [],
        "cultural_themes": [],
        "comparison_artists": [],
        "sensory_motifs": [],
        "artist_voice": "",
        "recommended_angle": "",
        "note": "heuristic — no ANTHROPIC_API_KEY set",
    }


# --- Stage 2 --------------------------------------------------------------

def generate(db: Session, *, context: str, strategy: dict, params: dict,
             artist_id: int | None = None, learning: dict | None = None,
             avoid_openings: list[str] | None = None) -> list[str]:
    """Return 2-3 raw pitch drafts. This artist's own high-rated/edited pitches are
    prepended as few-shot context, and their learning summary steers the prose, so
    edits and stars influence the next batch (the learning loop)."""
    if not ai.available():
        return []
    num = max(2, min(3, int(params.get("num_options", 3))))
    examples = feedback_logic.few_shot_examples(
        db, artist_id=artist_id, archetype=strategy.get("archetype"))
    system = prompts.GENERATOR_SYSTEM
    block = feedback_logic.few_shot_block(examples)
    if block:
        system = f"{system}\n\n{block}"
    # learning context: label-wide house rules first, then this artist's own
    house_row = db.get(models.HouseStyle, 1)
    learn = "\n".join(x for x in (
        feedback_logic.house_guidance(house_row.summary if house_row else None),
        feedback_logic.learning_guidance(learning),
    ) if x)
    prompt = prompts.generator_prompt(
        context=context, strategy=strategy, num_options=num,
        length=params.get("length", "150-200 words"),
        style=params.get("style", "match"),
        angle=params.get("angle", ""),
        descriptors=params.get("descriptors", []),
        learning=learn,
        avoid_openings=avoid_openings,
    )
    # multi-paragraph prose doesn't survive a JSON array (real newlines break the
    # parse), so the generator returns delimiter-separated plain text.
    try:
        raw = ai.complete(
            prompt, model=settings.ai_generate_model, system=system, max_tokens=4000,
        )
    except Exception:
        log.exception("generator AI call failed")
        return []
    parts = re.split(r"(?im)^[ \t]*=+\s*pitch\s*=+[ \t]*$", raw)
    drafts = [p.strip() for p in parts if p.strip()]
    return drafts[:num]


# --- Stage 3 --------------------------------------------------------------

def audit(draft: str, tag_phrases: list[str] | None = None) -> tuple[str, list[str]]:
    """Scrub AI/PR clichés. Deterministic scan first (always), then an LLM rewrite
    when a key is present. `tag_phrases` are the theme tags that must not appear
    verbatim in the prose. Returns (polished_text, phrases_removed)."""
    flagged = audit_logic.scan(draft)
    # only bother the audit with tags that actually leaked into the draft
    leaked = [t for t in (tag_phrases or []) if t.lower() in draft.lower()]
    if not ai.available():
        cleaned, removed = audit_logic.strip_deterministic(draft)
        return cleaned, removed
    try:
        polished = ai.complete(
            prompts.audit_prompt(draft, flagged, leaked or None),
            model=settings.ai_audit_model,
            system=prompts.AUDIT_SYSTEM,
            max_tokens=2000,
        ).strip()
    except Exception:
        log.exception("audit AI call failed; falling back to deterministic strip")
        polished = ""
    if not polished:  # empty rewrite — never ship worse than the deterministic strip
        return audit_logic.strip_deterministic(draft)
    # always-on backstop: guarantee no em/en dashes ship even past the LLM audit
    polished = audit_logic.dewatermark(polished).strip()
    # what did the audit actually clear out?
    still = set(audit_logic.scan(polished))
    removed = [p for p in flagged if p not in still]
    return polished, removed


# --- learning insights ----------------------------------------------------

def refresh_insights(db: Session, artist_id: int) -> dict:
    """Recompute the artist's "what worked / what didn't" summary from their
    feedback and persist it on the artist. Returns the summary (possibly empty)."""
    artist = db.get(models.Artist, artist_id)
    if artist is None:
        return {}
    signal = feedback_logic.learning_signal(db, artist_id)
    if not signal or not ai.available():
        return artist.learning_summary or {}
    prev = artist.learning_summary or {}
    if prev.get("rejected"):
        signal["user_rejected_rules"] = prev["rejected"]
    pinned = (prev.get("pinned_worked") or []) + (prev.get("pinned_avoid") or [])
    if pinned:
        signal["user_pinned_rules"] = pinned
    try:
        out = ai.complete_json(
            prompts.insights_prompt(signal), model=settings.ai_classify_model,
            system=prompts.INSIGHTS_SYSTEM, max_tokens=800,
        )
    except Exception:
        log.exception("insights AI call failed; keeping previous summary")
        out = None
    if isinstance(out, dict):
        worked = [str(x).strip() for x in (out.get("worked") or []) if str(x).strip()]
        avoid = [str(x).strip() for x in (out.get("avoid") or []) if str(x).strip()]
        # user curation survives every refresh: rejected stays gone, pinned stays
        worked, avoid, carry = feedback_logic.apply_curation(prev, worked, avoid)
        summary = {
            "blurb": str(out.get("blurb", "")).strip(),
            "worked": worked,
            "avoid": avoid,
            "avg_rating": signal.get("avg_rating"),
            "count": signal.get("count"),
            **carry,
        }
        artist.learning_summary = summary
        db.commit()
        return summary
    return artist.learning_summary or {}


def refresh_house_rules(db: Session) -> dict:
    """Re-generalize the label-wide house rules from every artist's feedback and
    the user's written comments; persist on the HouseStyle singleton. Runs after
    per-artist insights so the freshest summaries feed in."""
    row = db.get(models.HouseStyle, 1)
    signal = feedback_logic.house_signal(db)
    if not signal or not ai.available():
        return (row.summary if row else {}) or {}
    prev = (row.summary if row else {}) or {}
    if prev.get("rejected"):
        signal["user_rejected_rules"] = prev["rejected"]
    pinned = (prev.get("pinned_worked") or []) + (prev.get("pinned_avoid") or [])
    if pinned:
        signal["user_pinned_rules"] = pinned
    try:
        out = ai.complete_json(
            prompts.house_rules_prompt(signal), model=settings.ai_classify_model,
            system=prompts.HOUSE_SYSTEM, max_tokens=700,
        )
    except Exception:
        log.exception("house-rules AI call failed; keeping previous summary")
        out = None
    if row is None:
        row = models.HouseStyle(id=1)
        db.add(row)
    if isinstance(out, dict):
        worked = [str(x).strip() for x in (out.get("worked") or []) if str(x).strip()]
        avoid = [str(x).strip() for x in (out.get("avoid") or []) if str(x).strip()]
        worked, avoid, carry = feedback_logic.apply_curation(prev, worked, avoid)
        row.summary = {
            "blurb": str(out.get("blurb", "")).strip(),
            "worked": worked,
            "avoid": avoid,
            "avg_rating": signal.get("avg_rating"),
            "count": signal.get("rated_count"),
            **carry,
        }
        db.commit()
        return row.summary
    return row.summary or {}


# --- Orchestrator ---------------------------------------------------------

def run_pipeline(db: Session, *, context: str, params: dict,
                 artist_id: int | None = None, learning: dict | None = None,
                 avoid_openings: list[str] | None = None) -> dict:
    """Stage 1 → 2 → 3, returning the strategy and the audited options. Callers
    persist the result; this function itself does no DB writes."""
    strategy = classify(context)
    drafts = generate(db, context=context, strategy=strategy, params=params,
                      artist_id=artist_id, learning=learning,
                      avoid_openings=avoid_openings)
    options = []
    tags = [str(d) for d in (params.get("descriptors") or [])]
    for draft in drafts:
        polished, removed = audit(draft, tag_phrases=tags)
        options.append({"raw_llm_output": draft, "audited_output": polished,
                        "audit_removed": removed})
    note = None
    if not ai.available():
        note = ("No ANTHROPIC_API_KEY set — returned the strategy from a heuristic; "
                "no drafts were generated. Set a key to produce pitches.")
    elif not options:
        note = ("The AI request didn't complete (rate limit or network hiccup) — "
                "no drafts this time. Try again in a moment.")
    return {"strategy": strategy, "options": options, "note": note}
