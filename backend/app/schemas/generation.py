from pydantic import BaseModel, Field


class RSSSource(BaseModel):
    id: str
    name: str
    url: str
    category: str


class RSSSourceListResponse(BaseModel):
    sources: list[RSSSource]


class GenerationTriggerRequest(BaseModel):
    rss_source: str = Field(default="default")
    topic: str = Field(default="daily-news")


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
