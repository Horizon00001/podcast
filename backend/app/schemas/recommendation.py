from pydantic import BaseModel


class RecommendationItem(BaseModel):
    podcast_id: int
    score: float
    reason: str


class RecommendationResponse(BaseModel):
    user_id: int
    strategy: str
    items: list[RecommendationItem]
