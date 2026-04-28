from datetime import datetime

from pydantic import BaseModel


class LikeCreate(BaseModel):
    user_id: int
    podcast_id: int


class LikeResponse(LikeCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
