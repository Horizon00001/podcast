from sqlalchemy.orm import Session

from app.models.favorite import Favorite
from app.schemas.favorite import FavoriteCreate


class FavoriteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_favorites_by_user(self, user_id: int) -> list[Favorite]:
        return self.db.query(Favorite).filter(Favorite.user_id == user_id).all()

    def is_favorited(self, user_id: int, podcast_id: int) -> bool:
        return (
            self.db.query(Favorite)
            .filter(Favorite.user_id == user_id, Favorite.podcast_id == podcast_id)
            .first()
            is not None
        )

    def add_favorite(self, payload: FavoriteCreate) -> Favorite:
        existing = (
            self.db.query(Favorite)
            .filter(Favorite.user_id == payload.user_id, Favorite.podcast_id == payload.podcast_id)
            .first()
        )
        if existing:
            return existing
        record = Favorite(user_id=payload.user_id, podcast_id=payload.podcast_id)
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def remove_favorite(self, user_id: int, podcast_id: int) -> bool:
        record = (
            self.db.query(Favorite)
            .filter(Favorite.user_id == user_id, Favorite.podcast_id == podcast_id)
            .first()
        )
        if not record:
            return False
        self.db.delete(record)
        self.db.commit()
        return True
