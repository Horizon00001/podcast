from sqlalchemy.orm import Session

from app.models.podcast import Podcast
from app.schemas.podcast import PodcastCreate


class PodcastRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_podcasts(self) -> list[Podcast]:
        return self.db.query(Podcast).order_by(Podcast.published_at.desc()).all()

    def get_podcast(self, podcast_id: int) -> Podcast | None:
        return self.db.query(Podcast).filter(Podcast.id == podcast_id).first()

    def create_podcast(self, payload: PodcastCreate) -> Podcast:
        podcast = Podcast(title=payload.title, summary=payload.summary)
        self.db.add(podcast)
        self.db.commit()
        self.db.refresh(podcast)
        return podcast
