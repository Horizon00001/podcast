from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InteractionCreate(BaseModel):
    user_id: int
    podcast_id: int
    action: Literal["play", "pause", "resume", "like", "favorite", "skip", "complete"]
    listen_duration_ms: int | None = None
    progress_pct: float | None = None
    session_id: str | None = None
    context_hour: int | None = None
    context_weekday: int | None = None
    context_bucket: str | None = None


class InteractionResponse(InteractionCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
