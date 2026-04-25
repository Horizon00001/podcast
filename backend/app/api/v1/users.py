import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserPreferences, UserResponse


router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db)):
    user = User(username=payload.username, email=payload.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/by-username/{username}", response_model=UserResponse)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def _parse_preferences(raw_preferences: str | None) -> UserPreferences:
    if not raw_preferences:
        return UserPreferences()
    try:
        return UserPreferences.model_validate(json.loads(raw_preferences))
    except (json.JSONDecodeError, ValueError, TypeError):
        return UserPreferences()


@router.get("/{user_id}/preferences", response_model=UserPreferences)
def get_user_preferences(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _parse_preferences(user.preferences)


@router.put("/{user_id}/preferences", response_model=UserPreferences)
def update_user_preferences(payload: UserPreferences, user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.preferences = payload.model_dump_json()
    db.commit()
    return payload
