from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.init_db import apply_migrations, initialize_schema


app = FastAPI(title=settings.app_name)


def bootstrap_database() -> None:
    initialize_schema()
    apply_migrations()


bootstrap_database()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


app.include_router(api_router, prefix=settings.api_prefix)

# 挂载音频静态文件
audio_dir = settings.audio_dir
audio_dir.mkdir(parents=True, exist_ok=True)

podcast_audio_dir = settings.output_dir / "podcasts"
podcast_audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio/podcasts", StaticFiles(directory=str(podcast_audio_dir)), name="podcast_audio")

app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")
