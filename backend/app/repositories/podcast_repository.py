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

    def get_by_event_key(self, event_key: str) -> Podcast | None:
        if not event_key:
            return None
        return self.db.query(Podcast).filter(Podcast.event_key == event_key).first()

    def create_podcast(self, payload: PodcastCreate) -> Podcast:
        podcast = Podcast(
            title=payload.title,
            summary=payload.summary,
            category=payload.category,
            event_key=payload.event_key,
            audio_url=payload.audio_url,
            script_path=payload.script_path,
        )
        self.db.add(podcast)
        self.db.commit()
        self.db.refresh(podcast)
        return podcast

    def update_podcast(self, podcast: Podcast, payload: PodcastCreate) -> Podcast:
        podcast.title = payload.title
        podcast.summary = payload.summary
        podcast.category = payload.category
        podcast.event_key = payload.event_key
        podcast.audio_url = payload.audio_url
        podcast.script_path = payload.script_path
        self.db.add(podcast)
        self.db.commit()
        self.db.refresh(podcast)
        return podcast
