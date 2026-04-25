from typing import List

from pydantic import BaseModel, Field

from app.schemas.user import CustomRSSSource


class RSSSource(BaseModel):
    id: str
    name: str
    url: str
    category: str


class RSSSourceListResponse(BaseModel):
    sources: List[RSSSource]


class TopicOption(BaseModel):
    id: str
    name: str
    description: str


class TopicOptionListResponse(BaseModel):
    topics: List[TopicOption]


class GenerationTriggerRequest(BaseModel):
    rss_source: str = Field(default="default")
    topic: str = Field(default="daily-news")
    user_id: int | None = None
    use_subscriptions: bool = False
    custom_rss: list[CustomRSSSource] = []


class GenerationTriggerResponse(BaseModel):
    task_id: str
    status: str
    message: str


class GenerationTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: str
    rss_source: str
    topic: str
    created_at: str
    updated_at: str
