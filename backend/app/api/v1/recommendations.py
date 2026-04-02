from fastapi import APIRouter

from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import RecommendationService


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{user_id}", response_model=RecommendationResponse)
def get_recommendations(user_id: int):
    service = RecommendationService()
    return service.hot_recommendations(user_id=user_id)
