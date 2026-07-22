"""Pitchsmith backend — an LLM pipeline that turns artist background docs into
tailored, anti-AI music PR pitches.

A separate app for now, but built on the Label OS spine (FastAPI + lifespan,
SQLAlchemy, the native Anthropic wrapper) so it can be merged in later with
minimal friction. Serves the API on localhost and, when frontend/dist exists,
the built UI too.
"""
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from sqlalchemy import inspect as sa_inspect, text

from .config import settings
from .db import engine, ModelBase
from . import models  # noqa: F401 — registers tables on ModelBase.metadata
from .api.routes import router

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

# additive column migrations for existing databases (SQLite + Postgres safe)
MIGRATIONS = {
    "artists": [("context", "TEXT DEFAULT ''"),
                ("learning_summary", "JSON DEFAULT '{}'")],
    "user_feedback": [("comment", "TEXT DEFAULT ''"),
                      ("edit_kinds", "JSON DEFAULT '[]'")],
}


def migrate_columns() -> None:
    insp = sa_inspect(engine)
    known = set(insp.get_table_names())
    with engine.connect() as con:
        for table, cols in MIGRATIONS.items():
            if table not in known:
                continue  # create_all made the full current shape
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols:
                if name not in existing:
                    con.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
        con.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    ModelBase.metadata.create_all(engine)
    migrate_columns()
    yield


app = FastAPI(title="Pitchsmith", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:5174"],
    allow_methods=["*"], allow_headers=["*"], allow_credentials=True,
)
app.include_router(router)

if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="ui")


def run() -> None:
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, reload=False)


if __name__ == "__main__":
    run()
