"""Pitchsmith store — the four tables from the spec, in the Label OS style
(SQLAlchemy 2.0 Mapped columns, JSON where the shape is flexible, UTC stamps).

  artists        — basic metadata
  generations    — one run of the pipeline (input + chosen strategy + params)
  pitch_options  — the 2-3 audited drafts a run produced
  user_feedback  — the human edit / rating that closes the learning loop
"""
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import ModelBase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Artist(ModelBase):
    __tablename__ = "artists"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    genre: Mapped[str] = mapped_column(String(120), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    # the reusable sheet/context for this artist's project (last analyzed sheet),
    # so "new pitch" and "generate more" don't need a re-upload every time
    context: Mapped[str] = mapped_column(Text, default="")
    # what the team's edits + ratings taught us: {blurb, worked[], avoid[], guidance}
    learning_summary: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    generations: Mapped[list["Generation"]] = relationship(back_populates="artist")


class Generation(ModelBase):
    __tablename__ = "generations"
    id: Mapped[int] = mapped_column(primary_key=True)
    artist_id: Mapped[int | None] = mapped_column(ForeignKey("artists.id"), nullable=True)
    raw_input_context: Mapped[str] = mapped_column(Text, default="")
    archetype_selected: Mapped[str] = mapped_column(String(40), default="")
    # the full Stage-1 strategy payload (key_anchors, press_quotes, themes, angle)
    strategy: Mapped[dict] = mapped_column(JSON, default=dict)
    generation_parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    artist: Mapped["Artist"] = relationship(back_populates="generations")
    options: Mapped[list["PitchOption"]] = relationship(
        back_populates="generation", cascade="all, delete-orphan")


class PitchOption(ModelBase):
    __tablename__ = "pitch_options"
    id: Mapped[int] = mapped_column(primary_key=True)
    generation_id: Mapped[int] = mapped_column(ForeignKey("generations.id"))
    raw_llm_output: Mapped[str] = mapped_column(Text, default="")     # Stage 2 draft
    audited_output: Mapped[str] = mapped_column(Text, default="")     # Stage 3 polished
    # phrases the audit removed — provenance for the "why did this change" view
    audit_removed: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(12), default="pending")  # accepted|edited|rejected|pending
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    generation: Mapped["Generation"] = relationship(back_populates="options")
    feedback: Mapped[list["UserFeedback"]] = relationship(
        back_populates="option", cascade="all, delete-orphan")


class UserFeedback(ModelBase):
    __tablename__ = "user_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    pitch_option_id: Mapped[int] = mapped_column(ForeignKey("pitch_options.id"))
    final_user_edited_text: Mapped[str] = mapped_column(Text, default="")
    rating: Mapped[int] = mapped_column(Integer, default=0)  # 1-5 (0 = unrated)
    # free-text "what's working / what isn't" note — the strongest learning signal
    comment: Mapped[str] = mapped_column(Text, default="")
    # user-tagged genres of an edit (content, phrasing, style, grammar, facts,
    # length) so the learner attributes the change correctly
    edit_kinds: Mapped[list] = mapped_column(JSON, default=list)
    diff_analysis: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    option: Mapped["PitchOption"] = relationship(back_populates="feedback")


class HouseStyle(ModelBase):
    """Singleton row (id=1): the label-wide learning summary generalized from
    every artist's feedback — the rules that transfer to OTHER artists' pitches."""
    __tablename__ = "house_style"
    id: Mapped[int] = mapped_column(primary_key=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict)  # {blurb, worked[], avoid[], ...}
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow)
