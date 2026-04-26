from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class PodcastBase(BaseModel):
    title: str
    summary: str = ""
    category: str = "general"


class PodcastCreate(PodcastBase):
    event_key: str = ""
    audio_url: str = ""
    script_path: str = ""


class PodcastResponse(PodcastBase):
    id: int
    event_key: str = ""
    audio_url: str = ""
    script_path: str = ""
    published_at: datetime

    model_config = {"from_attributes": True}


class ScriptLineResponse(BaseModel):
    id: int
    speaker: Literal["host", "guest"]
    text: str
    startTime: int
    endTime: int
