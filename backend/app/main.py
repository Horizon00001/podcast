from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1.router import api_router
from app.core.config import settings
from app.db.init_db import init_db


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "env": settings.app_env}


app.include_router(api_router, prefix=settings.api_prefix)

# 挂载音频静态文件
project_root = Path(__file__).resolve().parents[2]
audio_dir = project_root / "output" / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")
