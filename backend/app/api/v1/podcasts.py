from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.podcast import PodcastCreate, PodcastResponse, ScriptLineResponse
from app.services.podcast_service import PodcastService


router = APIRouter(prefix="/podcasts", tags=["podcasts"])


@router.get("", response_model=list[PodcastResponse])
def list_podcasts(db: Session = Depends(get_db)):
    service = PodcastService(db)
    return service.list_podcasts()


@router.get("/{podcast_id}/script", response_model=list[ScriptLineResponse])
def get_podcast_script(podcast_id: int, db: Session = Depends(get_db)):
    service = PodcastService(db)
    podcast = service.get_podcast(podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    script_lines = service.get_podcast_script(podcast_id)
    if not script_lines:
        raise HTTPException(status_code=404, detail="Script not found for this podcast")
    return script_lines


@router.get("/{podcast_id}", response_model=PodcastResponse)
def get_podcast(podcast_id: int, db: Session = Depends(get_db)):
    service = PodcastService(db)
    podcast = service.get_podcast(podcast_id)
    if not podcast:
        raise HTTPException(status_code=404, detail="Podcast not found")
    return podcast


@router.post("", response_model=PodcastResponse, status_code=201)
def create_podcast(payload: PodcastCreate, db: Session = Depends(get_db)):
    service = PodcastService(db)
    return service.create_podcast(payload)
