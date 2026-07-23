"""The gold-pitch library: curated exemplars the writer imitates.

The model imitates examples far more faithfully than it follows rules, so this
library IS the voice. Retrieval is deterministic and free: score every active
exemplar by archetype match + word overlap between its tags/title/notes and the
brief's descriptors and motifs, take the top 2-3. No embeddings needed at this
scale; revisit if the library ever passes a few hundred entries.
"""
import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai import prompts
from .. import models

# The committed gold-pitch library — the versioned source of truth so every
# download/clone seeds the SAME curated set. Regenerate it from the current DB
# with backend/export_seed_exemplars.py, then commit it.
_SEED_FILE = Path(__file__).with_name("seed_exemplars.json")

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with",
    "artist", "music", "song", "album", "pitch", "pop",
}


def _tokens(*chunks: str) -> set[str]:
    out: set[str] = set()
    for c in chunks:
        out |= {w for w in re.findall(r"[a-z0-9]+", (c or "").lower())
                if len(w) > 2 and w not in _STOP}
    return out


# Fallback built-in set, used only if seed_exemplars.json is missing/unreadable.
# The JSON (loaded by _load_seed_specs) is the real, shippable source of truth.
_FALLBACK_SEED_EXEMPLARS = [
    dict(title="Sophia Stel — Molly In The Club (house reference)",
         text=prompts.GOLD_PITCH_1, archetype=prompts.ARCHETYPE_B,
         tags=["hyperpop", "diy pop", "y2k", "self-produced", "heavy press",
               "co-signs", "fashion", "tour", "vancouver", "a24"],
         notes="News-led, press-stacked one-sheet: single + video, then a dense "
               "run of outlets, co-signs, covers, and festival placements."),
    dict(title="Thoom — Everyday, everything is at stake (house reference)",
         text=prompts.GOLD_PITCH_2, archetype=prompts.ARCHETYPE_B,
         tags=["experimental", "arabic", "pop", "electronic", "thesis",
               "press quotes", "co-signs", "cultural identity"],
         notes="Thesis-driven: the artist's own quotes frame the record, then "
               "co-signs and tourmates stack the momentum."),
    dict(title="heartcoregirl — bloom (house reference)",
         text=prompts.GOLD_PITCH_3, archetype=prompts.ARCHETYPE_A,
         tags=["shoegaze trap", "underground", "diy", "dreamy", "introspective",
               "glasgow", "soundcloud scene", "emerging artist", "mixtape"],
         notes="Emerging/story: leads with the single + video, then the origin "
               "story in the underground scene and a first bit of press."),
    dict(title="Tiffany Day — HALO TOUR EUROPE (house reference)",
         text=prompts.GOLD_PITCH_4, archetype=prompts.ARCHETYPE_B,
         tags=["hyperpop", "electropop", "electroclash", "tour announcement",
               "charts", "co-signs", "heavy press", "sold out"],
         notes="Tour-announcement lead, then a two-year momentum case: charts, "
               "co-signs, and press stacked into an ascending arc."),
    dict(title="Cannelle — Dis Moi / CINNA (house reference)",
         text=prompts.GOLD_PITCH_5, archetype=prompts.ARCHETYPE_A,
         tags=["synth pop", "dance pop", "bilingual", "french", "rave",
               "modeling", "emerging artist", "mixtape", "flourish"],
         notes="Emerging with flourish: mixtape + single news, one artist quote, "
               "and colour that stays bolted to concrete facts."),
    dict(title="Quiet Light — Blue Angel Sparkling Silver 2 (house reference)",
         text=prompts.GOLD_PITCH_6, archetype=prompts.ARCHETYPE_B,
         tags=["folk electronic", "pop", "self-produced", "tour announcement",
               "press", "introspective", "narrative", "austin"],
         notes="Tour + mixtape news with full ticketing detail, then a narrative "
               "origin story anchored by a closing artist quote."),
    dict(title="Lelo — Get Geeked (house reference)",
         text=prompts.GOLD_PITCH_7, archetype=prompts.ARCHETYPE_B,
         tags=["rap", "ghettotech", "detroit", "electronic", "heavy streams",
               "co-signs", "tour", "festival", "established artist"],
         notes="Rap momentum: single + tour lead, then a dense case of streams, "
               "Pitchfork ratings, and co-signs from major artists."),
]


def _load_seed_specs() -> list[dict]:
    """The gold pitches to seed, from the committed JSON (source of truth). Falls
    back to the built-in list if the file is missing or unreadable."""
    try:
        data = json.loads(_SEED_FILE.read_text(encoding="utf-8"))
        specs: list[dict] = []
        for d in data:
            text = str(d.get("text", "")).strip()
            if not text:
                continue
            arch = d.get("archetype")
            specs.append(dict(
                title=str(d.get("title", "")).strip(),
                text=text,
                archetype=arch if arch in (prompts.ARCHETYPE_A, prompts.ARCHETYPE_B) else "",
                tags=[str(t).strip() for t in (d.get("tags") or []) if str(t).strip()],
                notes=str(d.get("notes", "")).strip(),
            ))
        if specs:
            return specs
    except Exception:
        pass
    return _FALLBACK_SEED_EXEMPLARS


def seed(db: Session) -> None:
    """Insert the built-in gold pitches when the library is empty, so retrieval
    and the manage-UI always have something to show. The set is the committed
    seed_exemplars.json, so every download gets the same curated library."""
    if db.scalar(select(models.Exemplar.id).limit(1)) is not None:
        return
    for spec in _load_seed_specs():
        db.add(models.Exemplar(source="seed", **spec))
    db.commit()


def pick(db: Session, strategy: dict, k: int = 2) -> list[models.Exemplar]:
    """The k most relevant active exemplars for this brief."""
    rows = db.scalars(select(models.Exemplar)
                      .where(models.Exemplar.active == 1)).all()
    if not rows:
        return []
    want = _tokens(
        " ".join(strategy.get("descriptors") or []),
        " ".join(strategy.get("sensory_motifs") or []),
        " ".join(strategy.get("cultural_themes") or []),
        strategy.get("artist_voice") or "",
    )
    arch = strategy.get("archetype", "")

    def score(ex: models.Exemplar) -> float:
        have = _tokens(" ".join(ex.tags or []), ex.title, ex.notes)
        overlap = len(want & have)
        return (2.0 if ex.archetype == arch else 0.0) + overlap

    ranked = sorted(rows, key=lambda ex: (score(ex), ex.id), reverse=True)
    return ranked[:k]


def block(exemplars: list[models.Exemplar]) -> str:
    """Render retrieved exemplars into the gold-examples prompt block. Falls back
    to the static built-in block when the library returned nothing."""
    if not exemplars:
        return prompts.GOLD_EXAMPLES
    lines = [
        "GOLD-STANDARD EXAMPLES - real pitches written in exactly the voice to "
        "aim for. Study how the sentences flow (connected, medium-length, "
        "relaxed), how every image says something true about the music, and how "
        "each pitch ends on the record or the momentum. Do NOT reuse their "
        "specific images, phrases, jokes, or openings in your own pitches, even "
        "when writing for the same artist. They calibrate the voice, nothing "
        "more."
    ]
    for i, ex in enumerate(exemplars, 1):
        arch = prompts.ARCHETYPES.get(ex.archetype, {}).get("name", "")
        label = f"EXAMPLE {i}" + (f" ({arch})" if arch else "")
        lines.append(f"\n{label}:\n{ex.text.strip()}")
    return "\n".join(lines)
