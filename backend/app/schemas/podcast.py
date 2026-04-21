from datetime import datetime

from pydantic import BaseModel


class PodcastBase(BaseModel):
    title: str
    summary: str = ""
    category: str = "general"


class PodcastCreate(PodcastBase):
    audio_url: str = ""
    script_path: str = ""


class PodcastResponse(PodcastBase):
    id: int
    audio_url: str = ""
    script_path: str = ""
    published_at: datetime

    model_config = {"from_attributes": True}
