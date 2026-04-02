from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class InteractionCreate(BaseModel):
    user_id: int
    podcast_id: int
    action: Literal["play", "like", "favorite", "skip"]


class InteractionResponse(InteractionCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}
