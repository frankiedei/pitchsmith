"""Regenerate app/logic/seed_exemplars.json from the current gold-pitch library.

Run this after curating gold pitches in the app, so the committed seed file (the
set every download/clone gets) matches your library:

    cd backend && .venv/bin/python export_seed_exemplars.py

Then commit and push app/logic/seed_exemplars.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.db import SessionLocal
from app import models
from app.logic.exemplars import _SEED_FILE


def main() -> None:
    db = SessionLocal()
    rows = db.query(models.Exemplar).order_by(models.Exemplar.id).all()
    out = [
        {
            "title": e.title,
            "text": e.text,
            "archetype": e.archetype,
            "tags": e.tags or [],
            "notes": e.notes or "",
        }
        for e in rows
    ]
    _SEED_FILE.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(out)} gold pitches to {_SEED_FILE}")
    print("Now commit + push it so downloads get your library:")
    print("  git add backend/app/logic/seed_exemplars.json && git commit -m 'Update gold pitches' && git push")


if __name__ == "__main__":
    main()
