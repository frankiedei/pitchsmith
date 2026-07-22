"""Feedback learning: turn past human edits + star ratings into (a) few-shot
context for future generations and (b) a plain-language "what worked / what
didn't" summary. This is the dynamic learning loop, now per-artist/project.
"""
import difflib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import prompts as ai_prompts
from ..config import settings
from .. import models


# --- rule hygiene -------------------------------------------------------------
# Every insights refresh re-infers similar lessons in slightly different words.
# Without semantic dedup they accumulate forever (the house list grew three
# paraphrases of "name the song in the opening sentence", all pinned), and the
# generator prompt drowns in near-identical directives.

def _norm(rule: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", rule.lower()).strip()


def is_duplicate_rule(a: str, b: str) -> bool:
    na, nb = _norm(a), _norm(b)
    if not na or not nb:
        return False
    if na in nb or nb in na:
        return True
    return difflib.SequenceMatcher(a=na, b=nb).ratio() >= 0.72


def dedupe_rules(rules: list[str], against: list[str] | None = None) -> list[str]:
    """Keep the first phrasing of each distinct rule; drop near-paraphrases,
    including ones already present in `against`."""
    kept: list[str] = []
    seen = list(against or [])
    for r in rules:
        r = str(r).strip()
        if r and not any(is_duplicate_rule(r, k) for k in seen + kept):
            kept.append(r)
    return kept


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
                      archetype: str | None = None,
                      exclude_texts: list[str] | None = None) -> list[dict]:
    """The best human-shipped pitches to steer new generations. Stars drive the
    order (higher rated first), so a 5-star edit pulls the next batch toward it.
    Prefers THIS artist's own history; falls back to same-archetype wins."""
    def is_gold(text: str) -> bool:
        # a user edit that is really a gold example pasted back in would appear
        # twice in the prompt ("follow closely" AND "never reuse its images")
        return any(
            difflib.SequenceMatcher(a=text[:600], b=g[:600]).ratio() > 0.6
            for g in ai_prompts.GOLD_PITCHES
        )

    def collect(rows) -> list[dict]:
        out = []
        for option, fb, gen in sorted(
            rows, key=lambda r: (r[1].rating, r[1].id), reverse=True
        ):
            text = fb.final_user_edited_text.strip()
            # winners only: a 1-star text labelled "follow more closely" pulls
            # the generator toward exactly what the user rejected
            if not text or (fb.rating or 0) < 4 or is_gold(text):
                continue
            out.append({"text": fb.final_user_edited_text, "rating": fb.rating,
                        "archetype": gen.archetype_selected})
        return out

    def is_dup(text: str, picked: list[dict]) -> bool:
        others = [p["text"] for p in picked] + list(exclude_texts or [])
        return any(
            difflib.SequenceMatcher(a=text[:600], b=o[:600]).ratio() > 0.6
            for o in others
        )

    # fetch a wide window and let the rating sort pick the winners — a narrow
    # newest-first window hides an older 5-star behind a run of recent rejects
    picked: list[dict] = []
    if artist_id is not None:
        for ex in collect(_feedback_rows(db, artist_id=artist_id, limit=40)):
            if not is_dup(ex["text"], picked):
                picked.append(ex)
    if len(picked) < settings.feedback_examples:  # top up with global winners
        for ex in collect(_feedback_rows(db, artist_id=None, limit=40)):
            if archetype and ex["archetype"] != archetype:
                continue
            if not is_dup(ex["text"], picked):
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


def contrast_pairs(db: Session, *, artist_id: int | None = None,
                   limit_pairs: int = 2) -> list[dict]:
    """Before/after pairs from the team's own edits: the draft we generated next
    to the 4+ star version the user shipped. The densest taste signal there is —
    it shows the model the direction of the edits instead of a distilled rule.
    Prefers this artist's pairs; tops up from the label."""
    def gather(rows, picked: list[dict]) -> None:
        for option, fb, _gen in sorted(
            rows, key=lambda r: (r[1].rating, r[1].id), reverse=True
        ):
            before = (option.audited_output or "").strip()
            after = fb.final_user_edited_text.strip()
            if not before or not after or (fb.rating or 0) < 4:
                continue
            sim = (fb.diff_analysis or {}).get("similarity")
            if sim is None:
                sim = difflib.SequenceMatcher(a=before, b=after).ratio()
            # a real edit: not untouched, not a wholesale paste-over
            if not (0.35 <= sim <= 0.985):
                continue
            if any(difflib.SequenceMatcher(a=after[:600], b=p["after"][:600])
                   .ratio() > 0.6 for p in picked):
                continue
            picked.append({"before": before[:1400], "after": after[:1400],
                           "rating": fb.rating})
            if len(picked) >= limit_pairs:
                return

    pairs: list[dict] = []
    if artist_id is not None:
        gather(_feedback_rows(db, artist_id=artist_id, limit=40), pairs)
    if len(pairs) < limit_pairs:
        gather(_feedback_rows(db, artist_id=None, limit=40), pairs)
    return pairs[:limit_pairs]


def contrast_block(pairs: list[dict]) -> str:
    """Render before/after pairs into a prompt fragment for the generator."""
    if not pairs:
        return ""
    lines = ["HOW THIS TEAM EDITS - real before/after edits the team made to "
             "earlier drafts. Learn the DIRECTION of the edits (what gets cut, "
             "what gets kept, how the sentences change) and write like the "
             "AFTER versions from the start. Do not copy their content or "
             "images into new pitches."]
    for i, p in enumerate(pairs, 1):
        lines.append(
            f"\n[Edit {i} - BEFORE (the draft they were handed)]\n{p['before']}"
            f"\n[Edit {i} - AFTER (what they shipped, rated {p['rating']}/5)]"
            f"\n{p['after']}")
    return "\n".join(lines)


def learning_signal(db: Session, artist_id: int) -> dict | None:
    """Assemble the raw feedback signal for one artist, for the insights model and
    the generator. Returns None when there's nothing to learn from yet."""
    rows = _feedback_rows(db, artist_id=artist_id, limit=40)
    if not rows:
        return None
    kept, rejected, edits, comments = [], [], [], []
    ratings = []
    reason_counts: dict[str, int] = {}
    for option, fb, _gen in rows:
        ratings.append(fb.rating)
        if fb.rating:
            (kept if fb.rating >= 4 else rejected if fb.rating <= 2 else kept).append(
                {"rating": fb.rating, "text": fb.final_user_edited_text[:600]})
        if option.status == "rejected":
            entry = {"rating": fb.rating, "text": option.audited_output[:400]}
            if fb.reject_reasons:
                entry["reasons"] = fb.reject_reasons
            rejected.append(entry)
        for r in (fb.reject_reasons or []):
            reason_counts[r] = reason_counts.get(r, 0) + 1
        if fb.comment.strip():
            comments.append({"rating": fb.rating, "comment": fb.comment.strip()[:400]})
        d = fb.diff_analysis or {}
        if d.get("added") or d.get("removed"):
            edits.append({"added": d.get("added", [])[:6],
                          "removed": d.get("removed", [])[:6],
                          "edit_kinds": fb.edit_kinds or []})
    rated = [r for r in ratings if r]
    signal = {
        "count": len(rows),
        "avg_rating": round(sum(rated) / len(rated), 2) if rated else None,
        "liked": kept[:6],
        "disliked": rejected[:6],
        "edits": edits[:8],
        "comments": comments[:10],
    }
    if reason_counts:
        signal["reject_reason_counts"] = reason_counts
    return signal


def merged_guidance(house: dict | None, artist: dict | None) -> str:
    """One short editor's-notes block for the generator: house and artist rules
    merged, semantically deduped (artist first, so its phrasing wins a tie), and
    capped. This replaces the old two-block approach that stacked up to 24
    overlapping directives in the prompt."""
    house, artist = house or {}, artist or {}
    do = dedupe_rules(
        (artist.get("worked") or []) + (house.get("worked") or []))[:6]
    avoid = dedupe_rules(
        (artist.get("avoid") or []) + (house.get("avoid") or []))[:6]
    if not do and not avoid:
        return ""
    parts = ["EDITOR'S NOTES, learned from this team's ratings and edits "
             "(follow them):"]
    if do:
        parts.append("Do: " + "; ".join(do) + ".")
    if avoid:
        parts.append("Avoid: " + "; ".join(avoid) + ".")
    return " ".join(parts)


# --- user curation of the learned rules --------------------------------------
# The worked/avoid lists are editable. A deleted rule goes to `rejected` (the
# refresh prompt is told never to re-derive it); a rule the user typed becomes
# `pinned` (refreshes always keep it verbatim). Both live inside the summary
# dict so they ride along wherever it is stored (artist or house singleton).

def curate_rules(summary: dict | None, worked: list[str], avoid: list[str]) -> dict:
    """Apply the user's edited lists to a summary, updating rejected/pinned."""
    worked = dedupe_rules(worked)[:10]
    avoid = dedupe_rules(avoid)[:10]
    s = dict(summary or {})
    old_w = s.get("worked") or []
    old_a = s.get("avoid") or []
    rejected = list(s.get("rejected") or [])
    kept_all = worked + avoid
    for gone in [w for w in old_w if w not in worked] + \
                [a for a in old_a if a not in avoid]:
        # a rule pruned because a near-identical one was kept is a dedup, not a
        # rejection — recording it as rejected made the refresh prompt see "never
        # do X" and "always do X" in almost the same words
        if any(is_duplicate_rule(gone, k) for k in kept_all):
            continue
        if gone not in rejected:
            rejected.append(gone)
    # re-adding a previously deleted rule (or a close paraphrase) un-rejects it
    rejected = [r for r in rejected
                if not any(is_duplicate_rule(r, k) for k in kept_all)]
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
    rejected = list(prev.get("rejected") or [])
    pw = dedupe_rules(prev.get("pinned_worked") or [])
    pa = dedupe_rules(prev.get("pinned_avoid") or [])

    def fresh(rules: list[str], pins: list[str]) -> list[str]:
        # drop anything the user rejected OR that merely re-words a pin
        return [r for r in dedupe_rules(rules, against=pins)
                if not any(is_duplicate_rule(r, x) for x in rejected)]

    worked_out = pw + fresh(worked, pw)
    avoid_out = pa + fresh(avoid, pa)
    carry = {"rejected": sorted(set(rejected))[-24:] if rejected else [],
             "pinned_worked": pw[:10], "pinned_avoid": pa[:10]}
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
    reason_counts: dict[str, int] = {}
    for _opt, fb, gen in _feedback_rows(db, artist_id=None, limit=80):
        if fb.comment.strip():
            comments.append({"rating": fb.rating,
                            "comment": fb.comment.strip()[:400]})
        if fb.rating:
            ratings.append(fb.rating)
        for r in (fb.reject_reasons or []):
            reason_counts[r] = reason_counts.get(r, 0) + 1
    if not per_artist and not comments:
        return None
    signal = {
        "artists": per_artist,
        "comments": comments[:20],
        "rated_count": len(ratings),
        "avg_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
    }
    if reason_counts:
        signal["reject_reason_counts"] = reason_counts
    return signal


# (house rules are rendered together with the artist's own rules by
# merged_guidance above, so the generator sees ONE deduped block, not two)
