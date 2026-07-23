# Pitchsmith

An LLM pipeline that turns artist background docs into tailored, anti-AI music
PR pitches. A **new, separate app** that inherits the Hallwood Label OS
architecture and UI — built to be merged into the main app later, but standalone
for now (its own `backend/` and `frontend/`, its own ports).

## Install (one line, always the latest)

Pitchsmith installs and updates from source, the same way Hallwood Label OS does:
a git checkout you run locally with a couple of scripts. Nothing is downloaded as
an app bundle, so macOS never quarantines it and every machine stays current with
one command. Needs `git`, `python3`, and `node` (on macOS: `brew install git python node`):

```bash
curl -fsSL https://raw.githubusercontent.com/frankiedei/pitchsmith/main/install.sh | bash
```

That clones Pitchsmith into `~/pitchsmith`, installs its dependencies on the
first run, builds the UI, and serves the app at http://127.0.0.1:8790. Prefer to
see what runs before running it? Do the same thing by hand:

```bash
git clone https://github.com/frankiedei/pitchsmith.git ~/pitchsmith
cd ~/pitchsmith && ./pitchsmith start
```

Because the install is a git checkout, you always get the newest code, and every
machine updates with one command:

```bash
cd ~/pitchsmith && ./pitchsmith update   # pull latest, rebuild, restart if running
```

Add your Anthropic API key to `~/pitchsmith/backend/.env` to generate pitches
(get one at console.anthropic.com). Without a key the app still runs, but only
the deterministic audit happens — no drafts are generated. Your data (pitches,
ratings, gold-pitch library) lives in `~/pitchsmith/backend/data` and survives
every update.

The `./pitchsmith` control script is the whole interface:

| Command | What it does |
|---|---|
| `./pitchsmith start` | Build the UI + run one server (UI + API) in the background → `:8790` |
| `./pitchsmith update` | `git pull`, reinstall deps, rebuild, restart if it was running |
| `./pitchsmith stop` / `restart` / `status` | Manage the background server |
| `./pitchsmith dev` | Foreground live-reload (backend `:8790` + Vite `:5174`) |
| `./pitchsmith logs` | Tail the server log |

> **Why not a `.app` download?** A double-click `Pitchsmith.app` is unsigned, so
> macOS Gatekeeper quarantines it on every machine but the one that built it
> ("can't be opened / from an unidentified developer"). The source install above
> avoids that entirely and is the supported path. If you *do* build one locally
> with `desktop/build-release.sh` and copy it to another Mac, clear the flag once
> with `xattr -dr com.apple.quarantine /Applications/Pitchsmith.app`.

## What it does

Paste an artist's bio, quotes and notes — or drop a one-sheet (`.pdf`/`.txt`) —
and the pipeline:

1. **Classifies the strategic angle** and extracts the raw material — the news
   hook and the concrete momentum (press, streaming/chart numbers, co-signs,
   tourmates) that build the artist's credibility (Stage 1).
   - **Archetype A — Story & Momentum**: emerging artists with thin press; lead
     with the release and the origin story, building credibility from the ground up.
   - **Archetype B — Authority & Press**: established artists with quotes,
     co-signs, or numbers; lead with the strongest leverage and stack it.
2. **Generates 2–3 distinct pitch options** in the house one-sheet voice, taught
   by a library of gold-standard reference pitches the writer imitates (Stage 2).
3. **Audits every draft** for AI/PR clichés; when one is flagged, the writer
   model surgically fixes only the offending sentences, leaving the rest intact
   (Stage 3).
4. **Records your edits, ratings, and one-tap reject reasons** so future drafts
   learn the house voice (gold-pitch retrieval + before/after learning loop).

Manage the reference pitches in the **Gold pitches** view — the single biggest
lever on quality. Everything AI degrades gracefully with no API key: the
deterministic cliché audit still runs and the classifier falls back to a heuristic.

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

The `./pitchsmith` control script (see the table under **Install**) is the whole
interface — `start` bootstraps the venv + `node_modules` on first run, then
serves the built UI **and** the API from one process on `http://127.0.0.1:8790`,
closest to how a packaged build behaves. Use `./pitchsmith dev` for live-reload
while editing the frontend.

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
