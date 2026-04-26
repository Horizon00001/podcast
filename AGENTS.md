# AGENTS.md

## Scope
- Repo split: `backend/` FastAPI app + CLI, `frontend/` standalone Vite/React app. No monorepo task runner.

## Source Of Truth
- Prefer executable config over docs. `README.md` and `CLAUDE.md` contain useful context, but some route and workflow details are stale.
- `frontend/README.md` is the default Vite template and can be ignored.

## Required Runtime
- Always use `backend/.venv/bin/python` for backend commands. The global Python environments are missing backend deps such as `pydantic_ai` and `dashscope`.
- Run backend commands from `backend/`. `Settings` loads `.env` from the current working directory.

## Backend Entry Points
- API app entrypoint: `backend/app/main.py`. Start with `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload`.
- Restart backend with `cd /home/default/Projects/podcast/backend && pkill -f "[u]vicorn app.main:app --host 0.0.0.0 --port 8000" || true && setsid .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/podcast_backend.log 2>&1 < /dev/null &`.
- CLI entrypoint: `cd backend && python -m app.cli --help`.
- Useful focused CLI commands:
  - `python -m app.cli fetch-rss`
  - `python -m app.cli generate-text --topic daily-news`
  - `python -m app.cli synthesize-tts --json-path output/podcast_script.json --output-dir output`
  - `python -m app.cli run-pipeline --topic daily-news`

## Config And Paths
- Default DB URL is `sqlite:///./podcast.db`, so the live SQLite file depends on cwd. Running from `backend/` uses `backend/podcast.db`.
- App startup always runs schema init plus migrations via `bootstrap_database()`. Expect DB side effects on app import/start.
- Repo-root paths matter:
  - RSS config: `config/feed.json`
  - Topics: `config/topics.json`
  - LLM prompt: `prompt.txt`
  - Generated output: `output/`
- Static audio mounts from repo-root output, not backend-local paths:
  - `/audio` -> `output/audio`
  - `/audio/podcasts` -> `output/podcasts`

## Pipeline Gotchas
- The generation flow is a real 4-step pipeline in `backend/app/pipelines/podcast_pipeline.py`, not 3 steps.
- Generation API behavior depends on the CLI pipeline log format. `frontend/src/pages/GeneratePage.tsx` parses exact markers like `[1/4]`, `[组开始]`, `[Script Start]`, `[TTS Done]`, `[Group Done]`. If you change backend log text, update the frontend parser too.
- `TTSService` expects an output parent dir and creates its own `audio/` subdir. Pass `output/`, not `output/audio/`.
- `ffmpeg` is required for audio merge steps.

## AI And TTS
- Script generation uses `pydantic-ai` with model `openai:deepseek-chat` from `backend/app/core/config.py`.
- TTS provider is selected by `TTS_PROVIDER` (`dashscope` or `edge`).
- Voice mapping is non-obvious: `male -> loongdavid_v2`, `female` or unset -> `longanwen`.

## Frontend
- Run all npm commands from `frontend/`.
- Main API client is `frontend/src/services/api.ts`.
- Default API base URL is `VITE_API_BASE_URL ?? http://localhost:8000/api/v1`.
- Media URLs intentionally strip `/api/v1` via `MEDIA_BASE_URL`; do not prepend the API prefix to audio asset URLs.
- Main router lives in `frontend/src/router/index.tsx`.

## Verification
- Backend test root is fixed by `backend/pytest.ini`; run tests from `backend/`.
- Common backend checks:
  - `pytest`
  - `pytest tests/test_health.py -v`
  - `pytest tests/test_generation_routes.py -v`
  - `pytest tests/test_podcast_routes.py -v`
  - `pytest tests/test_recommendation_routes.py -v`
  - `pytest tests/test_tts_provider.py -v`
- Backend tests use in-memory SQLite with `StaticPool` in `backend/tests/conftest.py`; they do not reuse `backend/podcast.db`.
- Frontend checks:
  - `npm run lint`
  - `npm run build`
  - `npm test`
- `npm run build` runs `tsc -b` before Vite build.

## Working Notes
- Root `package-lock.json` exists, but the active frontend project is `frontend/package.json`.
- Generated files under `output/` are artifacts, not source of truth, unless the task is explicitly about pipeline results.
