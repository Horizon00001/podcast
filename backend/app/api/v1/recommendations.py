from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import RecommendationService


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{user_id}", response_model=RecommendationResponse)
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    service = RecommendationService(db)
    return service.get_recommendations(user_id=user_id)
