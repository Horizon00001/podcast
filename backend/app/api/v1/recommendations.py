import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.recommendation import PreferenceRequest, RecommendationResponse
from app.services.recommendation_service import RecommendationService


router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/{user_id}", response_model=RecommendationResponse)
def get_recommendations(user_id: int, db: Session = Depends(get_db)):
    service = RecommendationService(db)
    return service.get_recommendations(user_id=user_id)


@router.post("/{user_id}/preferences")
def set_preferences(user_id: int, pref: PreferenceRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"ok": False, "error": "用户不存在"}

    user.preferences = json.dumps({"categories": pref.categories}, ensure_ascii=False)
    db.commit()
    return {"ok": True, "preferences": pref.categories}
