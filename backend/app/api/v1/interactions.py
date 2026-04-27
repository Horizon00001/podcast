from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.interaction_repository import InteractionRepository
from app.schemas.interaction import InteractionCreate, InteractionResponse
from app.services.podcast_stats import update_podcast_completion_stats


router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionResponse, status_code=201)
def report_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    repository = InteractionRepository(db)
    record = repository.create_interaction(payload)

    if payload.action in ("complete", "play", "skip") and payload.progress_pct is not None:
        update_podcast_completion_stats(db, payload.podcast_id)

    return record
