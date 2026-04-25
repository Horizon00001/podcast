from datetime import datetime

from pydantic import BaseModel


class FavoriteCreate(BaseModel):
    user_id: int
    podcast_id: int


class FavoriteResponse(FavoriteCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
