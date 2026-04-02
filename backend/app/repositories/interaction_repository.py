from sqlalchemy.orm import Session

from app.models.interaction import Interaction
from app.schemas.interaction import InteractionCreate


class InteractionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_interaction(self, payload: InteractionCreate) -> Interaction:
        record = Interaction(
            user_id=payload.user_id,
            podcast_id=payload.podcast_id,
            action=payload.action,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
