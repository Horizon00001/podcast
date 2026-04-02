from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.interaction_repository import InteractionRepository
from app.schemas.interaction import InteractionCreate, InteractionResponse


router = APIRouter(prefix="/interactions", tags=["interactions"])


@router.post("", response_model=InteractionResponse, status_code=201)
def report_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    repository = InteractionRepository(db)
    return repository.create_interaction(payload)
