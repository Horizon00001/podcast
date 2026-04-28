# AGENTS.md

## Scope
- Repo split: `backend/` FastAPI app + CLI, `frontend/` standalone Vite/React app. There is no monorepo task runner.

## Source Of Truth
- Prefer code and executable config over docs when they disagree.
- `README.md` and `CLAUDE.md` are useful context, but some older workflow notes may lag behind the implementation.
- `frontend/README.md` is the default Vite template and is not project documentation.

## Required Runtime
- Backend Python must come from `backend/.venv/bin/python` after creating the venv.
- Typical setup:
  - `cd /home/default/Projects/podcast/backend`
  - `python3 -m venv .venv`
  - `.venv/bin/pip install -r requirements.txt`
- Global Python environments are missing backend dependencies such as `pydantic_ai` and `dashscope`.
- Backend `.env` is loaded from `backend/.env` via `app/core/config.py`, so backend commands should still be run from `backend/`.

## Backend Entry Points
- API app entrypoint: `backend/app/main.py`
- Start backend from `backend/` with:
  - `.venv/bin/python -m uvicorn app.main:app --reload`
- CLI entrypoint:
  - `.venv/bin/python -m app.cli --help`
- Useful CLI commands:
  - `.venv/bin/python -m app.cli fetch-rss`
  - `.venv/bin/python -m app.cli generate-text --topic daily-news`
  - `.venv/bin/python -m app.cli synthesize-tts --json-path output/podcast_script.json --output-dir output`
  - `.venv/bin/python -m app.cli run-pipeline --topic daily-news`

## Config And Paths
- Default DB URL is `sqlite:///./podcast.db`, so the live SQLite file depends on the current working directory.
- When backend commands run from `backend/`, the SQLite file is `backend/podcast.db`.
- App import/startup runs `bootstrap_database()` immediately, which does schema init and migrations. Expect DB side effects when the app starts.
- Important repo-root paths:
  - RSS config: `config/feed.json`
  - Topics config: `config/topics.json`
  - Prompt file: `prompt.txt`
  - Generated output: `output/`
- Static audio mounts come from repo-root output paths, not backend-local paths:
  - `/audio` -> `output/audio`
  - `/audio/podcasts` -> `output/podcasts`

## API Surface
- API router lives in `backend/app/api/v1/router.py`.
- Current route groups included by the app:
  - `podcasts`
  - `users`
  - `interactions`
  - `recommendations`
  - `favorites`
  - `generation`
- Health endpoint is top-level `GET /health`.

## Pipeline Gotchas
- The generation flow is a 4-step pipeline in `backend/app/pipelines/podcast_pipeline.py`.
- Frontend generation progress depends on structured backend log markers. `frontend/src/pages/GeneratePage.tsx` reconstructs progress from streamed logs, so changing log formats can break the UI.
- `TTSService` expects a parent output dir and creates its own `audio/` subdir. Pass `output/`, not `output/audio/`.
- `ffmpeg` is required for final audio merge steps.

## AI And TTS
- Script generation uses model `openai:deepseek-chat` from `backend/app/core/config.py`.
- TTS provider is selected with `TTS_PROVIDER`.
- Supported provider names in the frontend capability types are `dashscope` and `edge`.
- Voice mapping is easy to miss:
  - `male -> loongdavid_v2`
  - `female` or unset -> `longanwen`

## Frontend
- Run all npm commands from `frontend/`.
- Main API client: `frontend/src/services/api.ts`
- Main router: `frontend/src/router/index.tsx`
- Current routed pages include:
  - `/` podcast list
  - `/podcasts/:id` podcast detail
  - `/generate` generation page
  - `/subscriptions` subscription management
  - `/models` provider/models page
  - `/settings` settings page
  - `/favorites` favorites page
- Default API base URL is `VITE_API_BASE_URL ?? http://localhost:8000/api/v1`.
- Media URLs intentionally strip `/api/v1` using `MEDIA_BASE_URL`; do not prepend the API prefix to audio asset URLs.

## Verification
- Backend tests must be run from `backend/` because `backend/pytest.ini` sets `pythonpath = .` and `testpaths = tests`.
- Common backend checks:
  - `.venv/bin/pytest`
  - `.venv/bin/pytest tests/test_health.py -v`
  - `.venv/bin/pytest tests/test_generation_routes.py -v`
  - `.venv/bin/pytest tests/test_podcast_routes.py -v`
  - `.venv/bin/pytest tests/test_recommendation_routes.py -v`
  - `.venv/bin/pytest tests/test_tts_provider.py -v`
- Frontend checks:
  - `npm run lint`
  - `npm run build`
  - `npm test`
- `npm run build` runs `tsc -b` before Vite build.

## Audio Assets
- Music assets are organized under `assets/audio/` by role:
  - `opening/` for intro/theme music
  - `transition/` for transition stings
  - `closing/` for ending music
- Selection strategy:
  - Prefer a random file from the role-specific directory
  - Fallback to candidates under `assets/audio/` root if the role directory is empty
- Current mix parameters by role:
  - `opening_theme`: `volume=0.24`, `fade_out=1800ms`
  - `transition_sting`: `volume=0.20`, `fade_out=350ms`
  - `closing_tail`: `volume=0.20`, `fade_out=2600ms`
  - other roles: `volume=0.22`, `fade_out=1300ms`

## Working Notes
- Root `package-lock.json` exists, but the active frontend project is `frontend/package.json`.
- Generated files under `output/` are artifacts, not source of truth, unless the task is explicitly about pipeline results.
- Some older docs still reference `/root/Projects/...`; in this environment the correct workspace path is `/home/default/Projects/podcast`.
