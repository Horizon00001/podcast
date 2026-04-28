from sqlalchemy.orm import Session

from app.models.like import Like
from app.schemas.like import LikeCreate


class LikeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_likes_by_user(self, user_id: int) -> list[Like]:
        return self.db.query(Like).filter(Like.user_id == user_id).all()

    def is_liked(self, user_id: int, podcast_id: int) -> bool:
        return (
            self.db.query(Like)
            .filter(Like.user_id == user_id, Like.podcast_id == podcast_id)
            .first()
            is not None
        )

    def add_like(self, payload: LikeCreate) -> Like:
        existing = (
            self.db.query(Like)
            .filter(Like.user_id == payload.user_id, Like.podcast_id == payload.podcast_id)
            .first()
        )
        if existing:
            return existing
        record = Like(user_id=payload.user_id, podcast_id=payload.podcast_id)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def remove_like(self, user_id: int, podcast_id: int) -> bool:
        record = (
            self.db.query(Like)
            .filter(Like.user_id == user_id, Like.podcast_id == podcast_id)
            .first()
        )
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True
