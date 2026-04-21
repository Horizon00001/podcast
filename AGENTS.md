# AGENTS.md

## Scope
- This repo is split into a Python backend in `backend/`, a Vite React frontend in `frontend/`, and root-level pipeline scripts (`main.py`, `rss_fetch.py`, `generate_text.py`, `tts_synthesize.py`). There is no monorepo task runner.

## Source Of Truth
- Treat executable config as authoritative over docs. The root `README.md` is partially aspirational: it mentions routes and files that do not all match the current code.
- There are no repo-local OpenCode, Cursor, Copilot, Claude, CI, or pre-commit instruction files as of now.

## Backend
- Backend app entrypoint is `backend/app/main.py`; run it from `backend/` with `uvicorn app.main:app --reload`.
- `Settings` loads `.env` from the current working directory. For backend runs from `backend/`, keep the env file there or export vars in the shell.
- Default database URL is `sqlite:///./podcast.db`, so the active SQLite file is relative to the process cwd. Running from `backend/` uses `backend/podcast.db`.
- Startup always calls `init_db()`, which runs `Base.metadata.create_all()` and then `run_migrations()`. Expect schema side effects on app start and in tests.
- Static audio is served from `/audio` using the repo root `output/audio` directory, not `backend/output`.

## Python Runtime
- **Always use the backend venv Python**: `/home/default/Projects/podcast/backend/.venv/bin/python`
- The root conda env (`/home/default/miniconda3/`, Python 3.13) and system pip (Python 3.8) both lack `pydantic_ai` and other deps. Using the wrong Python causes `ModuleNotFoundError: pydantic_ai` or `dashscope`.
- Activate venv: `cd backend && source .venv/bin/activate`
- Key binaries in `.venv/bin/`: `python`, `pytest`, `uvicorn`, `dashscope`
- Venv packages installed during development: `dashscope` (upgraded to 1.25.17), `mutagen`, `imageio_ffmpeg`
- `requirements.txt` lags behind: `dashscope` listed as `1.24.2` but installed as `1.25.17`; `mutagen` and `imageio_ffmpeg` not listed at all

## TTS Provider Abstraction
- `SpeechProvider` protocol in `backend/app/services/speech_provider.py` defines `async synthesize(text, output_path, voice, style)`.
- `create_speech_provider()` reads `TTS_PROVIDER` env var (`dashscope` or `edge`).
- `DashScopeTTSProvider` uses Alibaba DashScope `cosyvoice-v2`; `EdgeTTSProvider` is the fallback.
- Voice resolution: `voice="male"` → `loongdavid_v2`; `voice="female"` or unset → `longanwen`.
- DashScope config lives in `.env`, `.env.example`, and `backend/app/core/config.py`; all must be kept in sync.

## Pipeline
- The generation API shells out to `python -u main.py` from the repo root and streams stdout over SSE.
- Root `main.py` actually runs 4 steps (comment says `[1/3]` — out of date).
- Pipeline inputs/outputs: `config/feed.json`, `prompt.txt`, `output/audio/`.
- `config/feed.json` has one enabled source `espn-rpm`; frontend source picker reads it via `/api/v1/generation/sources`.
- Script generation uses `pydantic-ai` with `openai:deepseek-chat` and reads `prompt.txt` from repo root.
- TTS synthesis requires external `ffmpeg`; both the service class and root script call it via `subprocess.run(...)`.
- `TTSService` (`backend/app/services/tts_service.py`) constructs `audio_dir` as `output_dir / "audio"`. Callers should pass the parent `output/` dir, not `output/audio/`.

## Frontend
- Standalone npm project in `frontend/`; run all npm commands from that directory.
- Main router at `frontend/src/router/index.tsx`; `App.tsx` wraps routes with `UserProvider` and `PlayerProvider` and renders the persistent `GlobalPlayer`.
- API base URL: `http://localhost:8000/api/v1` in `frontend/src/services/api.ts`. Media URLs drop the `/api/v1` prefix.
- Generate page consumes SSE from `/generation/{task_id}/stream`; changing status/log behavior requires verifying `GeneratePage.tsx` SSE format.

## Verification
- Backend tests: from `backend/`, run `pytest`.
- Focused tests: `pytest tests/test_health.py`, `tests/test_generation_routes.py`, `tests/test_podcast_routes.py`, `tests/test_recommendation_routes.py`.
- TTS provider tests: `pytest tests/test_tts_provider.py`.
- Frontend: from `frontend/`, run `npm run lint` and `npm run build` (build first runs `tsc -b`).
- No frontend test runner configured.

## Security Note
- API keys (DashScope, MiniMax, etc.) may have been exposed in chat or written to `.env`. Rotate before production use.

## Working Notes
- `frontend/README.md` is the default Vite template and is not project guidance.
- `package-lock.json` exists at both the repo root and `frontend/`, but only `frontend/package.json` defines actual npm scripts and dependencies.
- Generated artifacts under `output/` are git-ignored; do not treat them as source files unless the task is explicitly about pipeline output.