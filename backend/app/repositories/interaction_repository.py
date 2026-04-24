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
            listen_duration_ms=payload.listen_duration_ms,
            progress_pct=payload.progress_pct,
            session_id=payload.session_id,
            context_hour=payload.context_hour,
            context_weekday=payload.context_weekday,
            context_bucket=payload.context_bucket,
            recommendation_request_id=payload.recommendation_request_id,
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record
