"""Database engine + session, inherited verbatim from the Label OS backend so a
later merge is a rename, not a rewrite. SQLite locally; Postgres when hosted."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings

engine = create_engine(
    settings.database_url,
    # timeout: wait for a concurrent writer instead of raising "database is
    # locked" (feedback saves + background learning refreshes can overlap)
    connect_args={"check_same_thread": False, "timeout": 30}
    if settings.database_url.startswith("sqlite") else {},
    pool_pre_ping=True,  # hosted Postgres: survive idle-connection resets
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class ModelBase(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
