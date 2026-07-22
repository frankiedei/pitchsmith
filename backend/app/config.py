"""Pitchsmith settings, loaded from environment / backend/.env.

Inherited shape from the Label OS backend: pydantic-settings reading a local
.env, SQLite by default, Postgres when DATABASE_URL points at one. Everything AI
degrades gracefully when no key is set — the deterministic anti-AI audit still
runs, so the pipeline never hard-fails on a missing credential.
"""
import os
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
# PITCHSMITH_DATA_DIR lets a packaged app keep its writable state (sqlite db)
# outside the (possibly read-only) app bundle — e.g. ~/Library/Application Support.
DATA_DIR = Path(os.environ.get("PITCHSMITH_DATA_DIR") or (BACKEND_DIR / "data"))
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    pass  # read-only location; DATABASE_URL is expected to point elsewhere


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- server ---
    host: str = "127.0.0.1"
    port: int = 8790  # LabelOS 8787, workflows 8791 — Pitchsmith takes 8790
    database_url: str = f"sqlite:///{DATA_DIR / 'pitchsmith.db'}"

    # --- Anthropic (pitch pipeline) ---
    # No key? The classifier/generator/LLM-audit are skipped and the endpoint
    # returns a clear note; the deterministic phrase audit still runs.
    anthropic_api_key: str = ""
    ai_generate_model: str = "claude-opus-4-8"            # Stage 2: quality tier
    ai_classify_model: str = "claude-haiku-4-5-20251001"  # Stage 1: cheap extract
    ai_audit_model: str = "claude-haiku-4-5-20251001"     # Stage 3: cheap rewrite
    # how many past accepted/edited pitches to feed back as few-shot context
    feedback_examples: int = 4

    # CORS origin for the Vite dev server
    frontend_origin: str = "http://localhost:5174"

    @field_validator("database_url", mode="before")
    @classmethod
    def _default_sqlite(cls, v):
        # An empty DATABASE_URL (blank line in .env, or an unset hosted var)
        # falls back to the local SQLite file rather than failing to parse.
        if not v or not str(v).strip():
            return f"sqlite:///{DATA_DIR / 'pitchsmith.db'}"
        return v


settings = Settings()


def reload_settings() -> None:
    """Re-read .env into the shared singleton (after a credentials change).
    Every AI call reads settings at call time, so a new key applies at once."""
    settings.__dict__.update(Settings().__dict__)
