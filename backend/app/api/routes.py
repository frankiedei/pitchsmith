"""Pitch API.

Composer flow: /analyze a sheet into clickable themes, then /generate (and
/generate-more) pitches for an artist. Every artist is a project: /artists lists
them, /artists/{id} is the pitch hub. Edits and star ratings feed back into the
next batch and into the artist's "what worked / didn't" insights.
"""
import json
import logging
import threading

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import SessionLocal, get_db
from .. import models, schemas
from ..ai import client as ai
from ..ai import pipeline
from ..ai import prompts
from ..logic import feedback as feedback_logic
from ..logic import parsing

log = logging.getLogger("pitchsmith.api")
router = APIRouter(prefix="/api/v1")


# strategy keys surfaced on the API (everything the UI may want to render)
_STRATEGY_KEYS = (
    "archetype", "key_anchors", "press_quotes", "cultural_themes",
    "comparison_artists", "sensory_motifs", "descriptors", "angle_options",
    "artist_voice", "recommended_angle", "note",
)


@router.get("/health")
def health() -> dict:
    return {"ok": True, "ai_key_set": ai.available(),
            "generate_model": pipeline.settings.ai_generate_model}


@router.get("/pitches/styles", response_model=list[schemas.StylePreset])
def styles() -> list[schemas.StylePreset]:
    """The style-preset options for the UI dropdown."""
    return [schemas.StylePreset(key=k, label=lbl, description=desc)
            for k, (lbl, desc) in prompts.STYLE_PRESETS.items()]


# --- shared helpers ---------------------------------------------------------

async def _read_input(request: Request) -> tuple[str, str, dict]:
    """Pull (context, artist_name, params) from either a JSON body or a multipart
    form with an optional .pdf/.txt upload. Shared by /analyze and /generate."""
    ctype = request.headers.get("content-type", "")
    if ctype.startswith("multipart/form-data"):
        form = await request.form()
        ctx = str(form.get("context") or "")
        name = str(form.get("artist_name") or "")
        raw_params = str(form.get("params") or "")
        params = json.loads(raw_params) if raw_params else {}
        parts: list[str] = []
        for upload in form.getlist("file"):  # one or many sheets
            if upload is not None and hasattr(upload, "read"):
                data = await upload.read()
                txt = parsing.extract_text(getattr(upload, "filename", "") or "", data)
                if txt.strip():
                    parts.append(txt)
        if parts:
            joined = "\n\n".join(parts)
            ctx = f"{ctx}\n\n{joined}".strip() if ctx else joined
        return ctx, name, params
    body = await request.json()
    return str(body.get("context") or ""), str(body.get("artist_name") or ""), \
        dict(body.get("params") or {})


def _get_or_create_artist(db: Session, name: str) -> models.Artist | None:
    name = (name or "").strip()
    if not name:
        return None
    artist = db.scalar(select(models.Artist).where(models.Artist.name == name))
    if artist is None:
        artist = models.Artist(name=name)
        db.add(artist)
        db.flush()
    return artist


def _insights_of(artist: models.Artist | None) -> schemas.Insights | None:
    s = (artist.learning_summary if artist else None) or {}
    if not (s.get("blurb") or s.get("worked") or s.get("avoid")):
        return None
    return schemas.Insights(
        blurb=s.get("blurb", ""), worked=s.get("worked", []),
        avoid=s.get("avoid", []), avg_rating=s.get("avg_rating"),
        count=s.get("count"))


def _latest_feedback(db: Session, option_id: int) -> models.UserFeedback | None:
    return db.scalar(
        select(models.UserFeedback)
        .where(models.UserFeedback.pitch_option_id == option_id)
        .order_by(models.UserFeedback.id.desc()).limit(1))


def _pitch_card(db: Session, option: models.PitchOption,
                gen: models.Generation) -> schemas.PitchCard:
    fb = _latest_feedback(db, option.id)
    text = fb.final_user_edited_text if (fb and fb.final_user_edited_text) \
        else option.audited_output
    params = gen.generation_parameters or {}
    return schemas.PitchCard(
        id=option.id, generation_id=option.generation_id, text=text,
        status=option.status, rating=fb.rating if fb else 0,
        comment=fb.comment if fb else "",
        angle=params.get("angle", ""), style=params.get("style", ""),
        audit_removed=option.audit_removed or [], created_at=option.created_at)


def _house_of(db: Session) -> schemas.HouseRules | None:
    row = db.get(models.HouseStyle, 1)
    s = (row.summary if row else None) or {}
    if not (s.get("blurb") or s.get("worked") or s.get("avoid")):
        return None
    return schemas.HouseRules(
        blurb=s.get("blurb", ""), worked=s.get("worked", []),
        avoid=s.get("avoid", []), avg_rating=s.get("avg_rating"),
        count=s.get("count"), updated_at=row.updated_at if row else None)


# --- analyze / suggest themes -----------------------------------------------

@router.post("/pitches/analyze", response_model=schemas.AnalyzeResponse)
async def analyze(request: Request):
    """Step 1 of the composer: read the uploaded sheet (or text), classify it, and
    return the clickable descriptors + smart-default angle/style. The UI holds the
    extracted `context` (hidden) and passes it back to /generate."""
    ctx, name, _ = await _read_input(request)
    if not ctx.strip():
        raise HTTPException(400, "Upload a .pdf/.txt sheet or provide some text.")
    strategy = pipeline.classify(ctx)
    return schemas.AnalyzeResponse(
        context=ctx, artist_name=name,
        archetype=strategy.get("archetype", ""),
        descriptors=strategy.get("descriptors", []),
        angle_options=strategy.get("angle_options", []),
        suggested_style=pipeline.suggested_style(strategy),
        artist_voice=strategy.get("artist_voice", ""),
        comparison_artists=strategy.get("comparison_artists", []),
        press_quotes=strategy.get("press_quotes", []),
        note=strategy.get("note"),
    )


@router.post("/pitches/suggest-themes", response_model=schemas.SuggestThemesResponse)
def suggest_themes(req: schemas.SuggestThemesRequest):
    """The 'more' button under the theme chips: additional tags from the sheet."""
    return schemas.SuggestThemesResponse(
        descriptors=pipeline.suggest_themes(req.context, req.existing))


# --- generate ---------------------------------------------------------------

@router.post("/pitches/generate", response_model=schemas.GenerateResponse)
async def generate(request: Request, db: Session = Depends(get_db)):
    """Run the 3-stage chain for an artist. Uses the artist's own past edits/stars
    (few-shot + learning summary) to steer the batch. Persists a Generation."""
    ctx, name, raw_params = await _read_input(request)
    if not ctx.strip():
        raise HTTPException(400, "Provide context text or upload a .pdf/.txt file.")

    params_dict = schemas.GenerateParams(**raw_params).model_dump()
    artist = _get_or_create_artist(db, name)
    if artist is not None:
        artist.context = ctx  # the project remembers its sheet for "generate more"
    learning = artist.learning_summary if artist else None

    result = pipeline.run_pipeline(
        db, context=ctx, params=params_dict,
        artist_id=artist.id if artist else None, learning=learning)

    gen = models.Generation(
        artist_id=artist.id if artist else None, raw_input_context=ctx,
        archetype_selected=result["strategy"].get("archetype", ""),
        strategy=result["strategy"], generation_parameters=params_dict)
    db.add(gen)
    db.flush()
    for opt in result["options"]:
        db.add(models.PitchOption(
            generation_id=gen.id, raw_llm_output=opt["raw_llm_output"],
            audited_output=opt["audited_output"], audit_removed=opt["audit_removed"]))
    db.commit()
    db.refresh(gen)

    strategy = dict(result["strategy"])
    strategy.setdefault("note", None)
    return schemas.GenerateResponse(
        generation_id=gen.id, artist_id=gen.artist_id,
        strategy=schemas.StrategyOut(**{k: strategy.get(k) for k in _STRATEGY_KEYS}),
        options=[schemas.PitchOptionOut.model_validate(o) for o in gen.options],
        note=result.get("note"))


@router.post("/pitches/generate-more", response_model=schemas.GenerateMoreResponse)
def generate_more(req: schemas.GenerateMoreRequest, db: Session = Depends(get_db)):
    """The button under the pitches: more options for the same generation, told to
    be different from the ones already there, reusing the stored strategy."""
    gen = db.get(models.Generation, req.generation_id)
    if gen is None:
        raise HTTPException(404, "generation not found")
    params = dict(gen.generation_parameters or {})
    params["num_options"] = req.num_options
    existing = [o.audited_output for o in gen.options]
    artist = db.get(models.Artist, gen.artist_id) if gen.artist_id else None
    learning = artist.learning_summary if artist else None

    drafts = pipeline.generate(
        db, context=gen.raw_input_context, strategy=dict(gen.strategy or {}),
        params=params, artist_id=gen.artist_id, learning=learning,
        avoid_openings=existing)
    tags = [str(d) for d in (params.get("descriptors") or [])]
    new_opts: list[models.PitchOption] = []
    for d in drafts:
        polished, removed = pipeline.audit(d, tag_phrases=tags)
        o = models.PitchOption(generation_id=gen.id, raw_llm_output=d,
                               audited_output=polished, audit_removed=removed)
        db.add(o)
        new_opts.append(o)
    db.commit()
    for o in new_opts:
        db.refresh(o)
    note = None if ai.available() else "No ANTHROPIC_API_KEY set — no pitches generated."
    return schemas.GenerateMoreResponse(
        generation_id=gen.id, note=note,
        options=[schemas.PitchOptionOut.model_validate(o) for o in new_opts])


# --- feedback ---------------------------------------------------------------

# The learning refreshes run AFTER the response (the save must feel instant and
# must never fail because an AI call did). One at a time — rapid star clicks
# queue rather than stampede SQLite and the API.
_refresh_lock = threading.Lock()


def _refresh_learning(artist_id: int | None, refresh_house: bool) -> None:
    with _refresh_lock:
        db = SessionLocal()
        try:
            if artist_id is not None:
                pipeline.refresh_insights(db, artist_id)
            if refresh_house:
                pipeline.refresh_house_rules(db)
        except Exception:
            log.exception("learning refresh failed (feedback itself was saved)")
        finally:
            db.close()


@router.post("/pitches/feedback", response_model=schemas.FeedbackResponse)
def feedback(req: schemas.FeedbackRequest, background: BackgroundTasks,
             db: Session = Depends(get_db)):
    """Record the edit / star rating / comment and return immediately; the
    artist's learning summary and the label-wide house rules refresh in the
    background so every next batch (for any artist) reflects what just landed."""
    option = db.get(models.PitchOption, req.pitch_option_id)
    if option is None:
        raise HTTPException(404, "pitch option not found")
    if req.status not in ("accepted", "edited", "rejected", "rated"):
        raise HTTPException(400, "status must be accepted, edited, rejected, or rated")

    final = req.final_user_edited_text or option.audited_output
    if req.status != "rated":  # a bare rating/comment doesn't accept or reject
        option.status = req.status
    diff = feedback_logic.diff_analysis(option.audited_output, final)
    fb = models.UserFeedback(
        pitch_option_id=option.id,
        final_user_edited_text=final if req.status != "rejected" else "",
        rating=req.rating, comment=req.comment.strip(),
        edit_kinds=[k.strip() for k in req.edit_kinds if k.strip()][:6],
        reject_reasons=[r.strip() for r in req.reject_reasons if r.strip()][:6],
        diff_analysis=diff)
    db.add(fb)
    db.commit()
    db.refresh(fb)

    gen = db.get(models.Generation, option.generation_id)
    artist_id = gen.artist_id if gen is not None else None
    # house rules re-generalize on the meaningful moments (comment or a
    # decision); a bare star rating refreshes only the artist's own summary
    refresh_house = bool(req.comment.strip()) or req.status != "rated"
    background.add_task(_refresh_learning, artist_id, refresh_house)

    insights = _insights_of(db.get(models.Artist, artist_id)) if artist_id else None
    return schemas.FeedbackResponse(
        id=fb.id, pitch_option_id=option.id, status=option.status,
        diff_analysis=diff, insights=insights, house=_house_of(db))


@router.get("/house-rules", response_model=schemas.HouseRules | None)
def house_rules(db: Session = Depends(get_db)):
    """The label-wide rules generalized from every artist's feedback."""
    return _house_of(db)


@router.put("/house-rules", response_model=schemas.HouseRules)
def update_house_rules(req: schemas.RulesUpdate, db: Session = Depends(get_db)):
    """The user's curated house lists. Deleted rules are remembered as rejected
    (refreshes won't re-derive them); added rules are pinned."""
    row = db.get(models.HouseStyle, 1)
    if row is None:
        row = models.HouseStyle(id=1)
        db.add(row)
    row.summary = feedback_logic.curate_rules(row.summary, req.worked, req.avoid)
    db.commit()
    s = row.summary
    return schemas.HouseRules(
        blurb=s.get("blurb", ""), worked=s.get("worked", []),
        avoid=s.get("avoid", []), avg_rating=s.get("avg_rating"),
        count=s.get("count"), updated_at=row.updated_at)


@router.put("/artists/{artist_id}/insights", response_model=schemas.Insights)
def update_insights(artist_id: int, req: schemas.RulesUpdate,
                    db: Session = Depends(get_db)):
    """The user's curated per-artist lists, same rejected/pinned semantics."""
    artist = db.get(models.Artist, artist_id)
    if artist is None:
        raise HTTPException(404, "artist not found")
    artist.learning_summary = feedback_logic.curate_rules(
        artist.learning_summary, req.worked, req.avoid)
    db.commit()
    s = artist.learning_summary
    return schemas.Insights(
        blurb=s.get("blurb", ""), worked=s.get("worked", []),
        avoid=s.get("avoid", []), avg_rating=s.get("avg_rating"),
        count=s.get("count"))


# --- gold-pitch library (exemplars) ------------------------------------------

@router.get("/exemplars", response_model=list[schemas.ExemplarOut])
def exemplars(db: Session = Depends(get_db)):
    """The gold-pitch library, newest first."""
    return db.scalars(select(models.Exemplar)
                      .order_by(models.Exemplar.id.desc())).all()


@router.post("/exemplars", response_model=schemas.ExemplarOut)
def add_exemplar(req: schemas.ExemplarIn, db: Session = Depends(get_db)):
    """Add a reference pitch. A cheap model auto-tags it (genres, moods,
    archetype) so retrieval can match it to future briefs; no key, no tags."""
    text = req.text.strip()
    if len(text) < 80:
        raise HTTPException(400, "Paste the full pitch text (at least a paragraph).")
    archetype, tags = "", []
    if ai.available():
        try:
            out = ai.complete_json(
                prompts.tag_exemplar_prompt(text),
                model=pipeline.settings.ai_classify_model,
                system=prompts.TAG_EXEMPLAR_SYSTEM, max_tokens=400)
            # the cheap model sometimes returns a bare tag array instead of the
            # {archetype, tags} object — accept either shape
            raw_tags = out if isinstance(out, list) else (
                out.get("tags") if isinstance(out, dict) else None)
            if isinstance(out, dict) and \
                    out.get("archetype") in (prompts.ARCHETYPE_A, prompts.ARCHETYPE_B):
                archetype = out["archetype"]
            tags = [str(t).strip() for t in (raw_tags or []) if str(t).strip()][:10]
        except Exception:
            log.exception("exemplar auto-tag failed; saving untagged")
    # if the tagger didn't commit to an archetype, fall back to the same
    # length/quote heuristic classify() uses, so retrieval still gets a signal
    if not archetype:
        archetype = pipeline._heuristic_strategy(text)["archetype"]
    ex = models.Exemplar(title=req.title.strip(), text=text,
                         notes=req.notes.strip(), archetype=archetype, tags=tags)
    db.add(ex)
    db.commit()
    db.refresh(ex)
    return ex


@router.put("/exemplars/{exemplar_id}", response_model=schemas.ExemplarOut)
def update_exemplar(exemplar_id: int, req: schemas.ExemplarUpdate,
                    db: Session = Depends(get_db)):
    """Toggle an exemplar in/out of retrieval without deleting it."""
    ex = db.get(models.Exemplar, exemplar_id)
    if ex is None:
        raise HTTPException(404, "exemplar not found")
    ex.active = 1 if req.active else 0
    db.commit()
    db.refresh(ex)
    return ex


@router.delete("/exemplars/{exemplar_id}")
def delete_exemplar(exemplar_id: int, db: Session = Depends(get_db)):
    ex = db.get(models.Exemplar, exemplar_id)
    if ex is None:
        raise HTTPException(404, "exemplar not found")
    db.delete(ex)
    db.commit()
    return {"ok": True}


# --- pitch hub (projects) ---------------------------------------------------

@router.get("/artists", response_model=list[schemas.ArtistSummary])
def artists(db: Session = Depends(get_db)):
    """Every artist/project, newest activity first, for the left sidebar."""
    arts = db.scalars(select(models.Artist).order_by(models.Artist.id.desc())).all()
    out: list[schemas.ArtistSummary] = []
    for a in arts:
        gens = sorted(a.generations, key=lambda g: g.id, reverse=True)
        gen_ids = [g.id for g in gens]
        count = 0
        avg = None
        last = a.created_at
        if gen_ids:
            count = db.scalar(select(func.count(models.PitchOption.id))
                              .where(models.PitchOption.generation_id.in_(gen_ids))) or 0
            avg = db.scalar(
                select(func.avg(models.UserFeedback.rating))
                .join(models.PitchOption,
                      models.PitchOption.id == models.UserFeedback.pitch_option_id)
                .where(models.PitchOption.generation_id.in_(gen_ids),
                       models.UserFeedback.rating > 0))
            last_opt = db.scalar(
                select(func.max(models.PitchOption.created_at))
                .where(models.PitchOption.generation_id.in_(gen_ids)))
            last = last_opt or last
        out.append(schemas.ArtistSummary(
            id=a.id, name=a.name,
            archetype=gens[0].archetype_selected if gens else "",
            pitch_count=count, avg_rating=round(avg, 2) if avg else None,
            last_activity=last))
    out.sort(key=lambda s: s.last_activity or 0, reverse=True)
    return out


@router.post("/artists/{artist_id}/reset")
def reset_artist(artist_id: int, background: BackgroundTasks,
                 db: Session = Depends(get_db)):
    """Fresh start: delete every generation, pitch, and feedback row for this
    artist and clear the learned insights. The artist and their sheet stay.
    House rules re-generalize in the background without this artist's signal."""
    artist = db.get(models.Artist, artist_id)
    if artist is None:
        raise HTTPException(404, "artist not found")
    for gen in list(artist.generations):
        db.delete(gen)  # cascades options -> feedback
    artist.learning_summary = {}
    db.commit()
    background.add_task(_refresh_learning, None, True)
    return {"ok": True}


@router.delete("/artists/{artist_id}")
def delete_artist(artist_id: int, background: BackgroundTasks,
                  db: Session = Depends(get_db)):
    """Remove the artist and everything under them (generations, pitches,
    feedback). House rules re-generalize in the background."""
    artist = db.get(models.Artist, artist_id)
    if artist is None:
        raise HTTPException(404, "artist not found")
    for gen in list(artist.generations):
        db.delete(gen)  # cascades options -> feedback
    db.delete(artist)
    db.commit()
    background.add_task(_refresh_learning, None, True)
    return {"ok": True}


@router.get("/artists/{artist_id}", response_model=schemas.ArtistDetail)
def artist_detail(artist_id: int, db: Session = Depends(get_db)):
    """The pitch hub for one artist: every pitch they've worked on, newest first,
    plus the learning insights."""
    artist = db.get(models.Artist, artist_id)
    if artist is None:
        raise HTTPException(404, "artist not found")
    gens = sorted(artist.generations, key=lambda g: g.id, reverse=True)
    cards: list[schemas.PitchCard] = []
    archetype = gens[0].archetype_selected if gens else ""
    for gen in gens:
        for opt in sorted(gen.options, key=lambda o: o.id, reverse=True):
            cards.append(_pitch_card(db, opt, gen))
    cards.sort(key=lambda c: c.created_at, reverse=True)
    return schemas.ArtistDetail(
        id=artist.id, name=artist.name, archetype=archetype,
        has_context=bool(artist.context), insights=_insights_of(artist),
        pitches=cards)
