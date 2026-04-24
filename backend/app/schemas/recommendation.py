from pydantic import BaseModel


class PreferenceRequest(BaseModel):
    categories: list[str]


class RecommendationItem(BaseModel):
    podcast_id: int
    score: float
    reason: str


class RecommendationResponse(BaseModel):
    user_id: int
    strategy: str
    request_id: str
    time_context: str = ""
    items: list[RecommendationItem]
