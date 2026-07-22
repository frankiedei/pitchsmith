"""Feedback learning: turn past human edits + star ratings into (a) few-shot
context for future generations and (b) a plain-language "what worked / what
didn't" summary. This is the dynamic learning loop, now per-artist/project.
"""
import difflib

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from .. import models


def diff_analysis(before: str, after: str) -> dict:
    """Cheap, deterministic diff signal stored alongside each edit: how much the
    user changed and which chunks they added/removed. Feeds later prompt tuning."""
    before, after = before or "", after or ""
    sm = difflib.SequenceMatcher(a=before, b=after)
    ratio = sm.ratio()
    added, removed = [], []
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op in ("replace", "insert") and after[b0:b1].strip():
            added.append(after[b0:b1].strip())
        if op in ("replace", "delete") and before[a0:a1].strip():
            removed.append(before[a0:a1].strip())
    return {
        "similarity": round(ratio, 3),
        "edit_distance": len(before) + len(after) - 2 * sum(
            blk.size for blk in sm.get_matching_blocks()
        ),
        "added": added[:12],
        "removed": removed[:12],
    }


def _feedback_rows(db: Session, *, artist_id: int | None, limit: int):
    """Latest (option, feedback, generation) rows, newest first. When artist_id is
    given, restrict to that artist's project."""
    stmt = (
        select(models.PitchOption, models.UserFeedback, models.Generation)
        .join(models.UserFeedback,
              models.UserFeedback.pitch_option_id == models.PitchOption.id)
        .join(models.Generation,
              models.Generation.id == models.PitchOption.generation_id)
        .order_by(models.UserFeedback.id.desc())
        .limit(limit)
    )
    if artist_id is not None:
        stmt = stmt.where(models.Generation.artist_id == artist_id)
    return db.execute(stmt).all()


def few_shot_examples(db: Session, *, artist_id: int | None = None,
                      archetype: str | None = None) -> list[dict]:
    """The best human-shipped pitches to steer new generations. Stars drive the
    order (higher rated first), so a 5-star edit pulls the next batch toward it.
    Prefers THIS artist's own history; falls back to same-archetype wins."""
    def collect(rows) -> list[dict]:
        out = []
        for option, fb, gen in sorted(
            rows, key=lambda r: (r[1].rating, r[1].id), reverse=True
        ):
            if not fb.final_user_edited_text.strip():
                continue
            out.append({"text": fb.final_user_edited_text, "rating": fb.rating,
                        "archetype": gen.archetype_selected})
        return out

    picked: list[dict] = []
    if artist_id is not None:
        picked = collect(_feedback_rows(db, artist_id=artist_id,
                                        limit=settings.feedback_examples * 3))
    if len(picked) < settings.feedback_examples:  # top up with global winners
        for ex in collect(_feedback_rows(db, artist_id=None,
                                         limit=settings.feedback_examples * 4)):
            if archetype and ex["archetype"] != archetype:
                continue
            if ex["text"] not in {p["text"] for p in picked}:
                picked.append(ex)
    return picked[: settings.feedback_examples]


def few_shot_block(examples: list[dict]) -> str:
    """Render examples into a prompt fragment the generator can prepend."""
    if not examples:
        return ""
    lines = ["Pitches this team actually shipped (higher rated = follow more "
             "closely). Match their voice, concreteness, and structure:"]
    for i, ex in enumerate(examples, 1):
        lines.append(f"\n[Example {i}, rated {ex['rating']}/5]\n{ex['text']}")
    return "\n".join(lines)


def learning_signal(db: Session, artist_id: int) -> dict | None:
    """Assemble the raw feedback signal for one artist, for the insights model and
    the generator. Returns None when there's nothing to learn from yet."""
    rows = _feedback_rows(db, artist_id=artist_id, limit=40)
    if not rows:
        return None
    kept, rejected, edits, comments = [], [], [], []
    ratings = []
    for option, fb, _gen in rows:
        ratings.append(fb.rating)
        if fb.rating:
            (kept if fb.rating >= 4 else rejected if fb.rating <= 2 else kept).append(
                {"rating": fb.rating, "text": fb.final_user_edited_text[:600]})
        if option.status == "rejected":
            rejected.append({"rating": fb.rating, "text": option.audited_output[:400]})
        if fb.comment.strip():
            comments.append({"rating": fb.rating, "comment": fb.comment.strip()[:400]})
        d = fb.diff_analysis or {}
        if d.get("added") or d.get("removed"):
            edits.append({"added": d.get("added", [])[:6],
                          "removed": d.get("removed", [])[:6],
                          "edit_kinds": fb.edit_kinds or []})
    rated = [r for r in ratings if r]
    return {
        "count": len(rows),
        "avg_rating": round(sum(rated) / len(rated), 2) if rated else None,
        "liked": kept[:6],
        "disliked": rejected[:6],
        "edits": edits[:8],
        "comments": comments[:10],
    }


def learning_guidance(summary: dict | None) -> str:
    """Render the stored learning_summary into a short instruction block that the
    generator prepends, so past edits and stars actually steer the next pitch."""
    if not summary:
        return ""
    worked = summary.get("worked") or []
    avoid = summary.get("avoid") or []
    if not worked and not avoid:
        return ""
    parts = ["What this team's edits and ratings have taught us for this artist "
             "(follow it):"]
    if worked:
        parts.append("Do more of: " + "; ".join(worked[:6]) + ".")
    if avoid:
        parts.append("Avoid: " + "; ".join(avoid[:6]) + ".")
    return " ".join(parts)


# --- user curation of the learned rules --------------------------------------
# The worked/avoid lists are editable. A deleted rule goes to `rejected` (the
# refresh prompt is told never to re-derive it); a rule the user typed becomes
# `pinned` (refreshes always keep it verbatim). Both live inside the summary
# dict so they ride along wherever it is stored (artist or house singleton).

def curate_rules(summary: dict | None, worked: list[str], avoid: list[str]) -> dict:
    """Apply the user's edited lists to a summary, updating rejected/pinned."""
    worked = [w.strip() for w in worked if w.strip()][:10]
    avoid = [a.strip() for a in avoid if a.strip()][:10]
    s = dict(summary or {})
    old_w = s.get("worked") or []
    old_a = s.get("avoid") or []
    rejected = list(s.get("rejected") or [])
    for gone in [w for w in old_w if w not in worked] + \
                [a for a in old_a if a not in avoid]:
        if gone not in rejected:
            rejected.append(gone)
    # re-adding a previously deleted rule un-rejects it
    rejected = [r for r in rejected if r not in worked and r not in avoid]
    pinned_w = [p for p in (s.get("pinned_worked") or []) if p in worked]
    pinned_w += [w for w in worked if w not in old_w and w not in pinned_w]
    pinned_a = [p for p in (s.get("pinned_avoid") or []) if p in avoid]
    pinned_a += [a for a in avoid if a not in old_a and a not in pinned_a]
    s.update({
        "worked": worked, "avoid": avoid, "rejected": rejected[-24:],
        "pinned_worked": pinned_w[:10], "pinned_avoid": pinned_a[:10],
    })
    return s


def apply_curation(summary_prev: dict | None, worked: list[str],
                   avoid: list[str]) -> tuple[list[str], list[str], dict]:
    """Filter freshly inferred lists through the user's curation: drop rejected
    rules, put pinned ones first. Returns (worked, avoid, carryover_keys)."""
    prev = summary_prev or {}
    rejected = set(prev.get("rejected") or [])
    pw = list(prev.get("pinned_worked") or [])
    pa = list(prev.get("pinned_avoid") or [])
    worked_out = pw + [w for w in worked if w not in rejected and w not in pw]
    avoid_out = pa + [a for a in avoid if a not in rejected and a not in pa]
    carry = {"rejected": sorted(rejected)[-24:] if rejected else [],
             "pinned_worked": pw, "pinned_avoid": pa}
    return worked_out[:8], avoid_out[:8], carry


# --- cross-artist (house) learning ------------------------------------------

def house_signal(db: Session) -> dict | None:
    """Aggregate the label-wide feedback signal: every artist's learning summary
    plus the user's written comments across all projects. None when there's
    nothing to generalize from yet."""
    per_artist = []
    for a in db.scalars(select(models.Artist)).all():
        s = a.learning_summary or {}
        if s.get("blurb") or s.get("worked") or s.get("avoid"):
            per_artist.append({
                "artist": a.name,
                "worked": (s.get("worked") or [])[:6],
                "avoid": (s.get("avoid") or [])[:6],
                "avg_rating": s.get("avg_rating"),
            })
    comments, ratings = [], []
    for _opt, fb, gen in _feedback_rows(db, artist_id=None, limit=80):
        if fb.comment.strip():
            comments.append({"rating": fb.rating,
                            "comment": fb.comment.strip()[:400]})
        if fb.rating:
            ratings.append(fb.rating)
    if not per_artist and not comments:
        return None
    return {
        "artists": per_artist,
        "comments": comments[:20],
        "rated_count": len(ratings),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }


def house_guidance(summary: dict | None) -> str:
    """Render the label-wide house rules into an instruction block prepended to
    EVERY generation, so what one artist's feedback taught carries to the rest."""
    if not summary:
        return ""
    worked = summary.get("worked") or []
    avoid = summary.get("avoid") or []
    if not worked and not avoid:
        return ""
    parts = ["House rules learned from this team's feedback across ALL artists "
             "(follow them in every pitch):"]
    if worked:
        parts.append("Do: " + "; ".join(worked[:6]) + ".")
    if avoid:
        parts.append("Avoid: " + "; ".join(avoid[:6]) + ".")
    return " ".join(parts)
