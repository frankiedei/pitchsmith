# Pitchsmith

An LLM pipeline that turns artist background docs into tailored, anti-AI music
PR pitches. A **new, separate app** that inherits the Hallwood Label OS
architecture and UI — built to be merged into the main app later, but standalone
for now (its own `backend/` and `frontend/`, its own ports).

## What it does

Paste an artist's bio, quotes and notes — or drop a one-sheet (`.pdf`/`.txt`) —
and the pipeline:

1. **Classifies the strategic angle** and extracts the raw material (Stage 1).
   - **Archetype A — Worldbuilding / Sensory**: emerging artists with thin press;
     fill the gap with concrete sensory imagery and visual anchors.
   - **Archetype B — Authority / Thesis**: established artists with quotes,
     co-signs, or metrics; lead with leverage and the artist's thesis.
2. **Generates 2–3 distinct pitch options** tailored to the archetype, length,
   and target outlet style (Stage 2).
3. **Audits every draft** against a banned-phrase list, replacing generic
   AI/PR clichés with concrete writing (Stage 3).
4. **Records your edits and ratings** so future drafts learn the house voice
   (dynamic few-shot feedback loop).

Everything AI degrades gracefully with no API key: the deterministic anti-AI
audit still runs and the classifier falls back to a heuristic.

## Architecture (inherited from Label OS)

- **Backend** — FastAPI + `lifespan`, `pydantic-settings` config from `.env`,
  SQLAlchemy 2.0 (SQLite local / Postgres hosted), and the native Anthropic
  wrapper (`ai/client.py`). The 3-stage chain lives in `ai/pipeline.py`; the
  archetypes, banned phrases and few-shot prompts in `ai/prompts.py`.
- **Frontend** — Vite + React 18 + Zustand + the shared `tokens.css` theme
  system, a typed `req<T>` API client, a composer → results two-pane screen.

```
pitchsmith/
  backend/
    app/
      main.py            FastAPI app (serves API + built UI)
      config.py db.py    settings + engine (Label OS shape)
      models.py          artists · generations · pitch_options · user_feedback
      schemas.py         Pydantic request/response models
      ai/
        client.py        thin Anthropic wrapper (inherited)
        pipeline.py      Stage 1 → 2 → 3 orchestrator
        prompts.py       archetypes, banned phrases, few-shot templates
      logic/
        parsing.py       .pdf/.txt context extraction
        audit.py         deterministic banned-phrase scan/strip
        feedback.py      few-shot retrieval + diff analysis
      api/routes.py      /api/v1/pitches/{generate,feedback,history} + /health
    requirements.txt  .env.example
  frontend/            Vite/React/Zustand UI shell
  dev.sh               run backend (8790) + frontend (5174) together
```

## Run it

Use the `pitchsmith` control CLI (bootstraps the venv + node_modules on first run):

```bash
cd pitchsmith
cp backend/.env.example backend/.env   # add ANTHROPIC_API_KEY

./pitchsmith start      # build the UI + run the server in the background → :8790
./pitchsmith stop       # stop the server
./pitchsmith restart    # stop, then start
./pitchsmith update     # pull latest, reinstall deps, rebuild, restart if running
./pitchsmith status     # is it running? where?
./pitchsmith dev        # foreground live-reload (backend :8790 + Vite :5174)
./pitchsmith logs       # tail the server log
```

`start` serves the built UI **and** the API from one process on
`http://127.0.0.1:8790` — closest to how a packaged build behaves. Use `dev`
for live-reload while editing the frontend.

To run it as a bare `pitchsmith` command from anywhere, put it on your PATH once:

```bash
ln -s "$PWD/pitchsmith" /usr/local/bin/pitchsmith   # then: pitchsmith start
```

## API

- `POST /api/v1/pitches/generate` — JSON `{context, artist_name, params}` **or**
  multipart with a `file` upload. Runs the 3-stage chain; returns the strategy
  and 2–3 audited options, all persisted.
- `POST /api/v1/pitches/feedback` — `{pitch_option_id, status, final_user_edited_text, rating}`.
  Saves the edit + a diff for future few-shot retrieval.
- `GET /api/v1/pitches/history` — recent generations.
- `GET /api/v1/health` — key status + active model.

## Ports

| App               | Backend | Frontend |
|-------------------|---------|----------|
| Label OS          | 8787    | 5173     |
| Workflow Packages | 8791    | —        |
| **Pitchsmith**    | 8790    | 5174     |
