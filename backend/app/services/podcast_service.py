from sqlalchemy.orm import Session

from app.repositories.podcast_repository import PodcastRepository
from app.schemas.podcast import PodcastCreate


class PodcastService:
    def __init__(self, db: Session):
        self.repository = PodcastRepository(db)

    def list_podcasts(self):
        return self.repository.list_podcasts()

    def get_podcast(self, podcast_id: int):
        return self.repository.get_podcast(podcast_id)

    def create_podcast(self, payload: PodcastCreate):
        return self.repository.create_podcast(payload)
