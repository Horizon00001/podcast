from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.like_repository import LikeRepository
from app.schemas.like import LikeCreate, LikeResponse

router = APIRouter(prefix="/likes", tags=["likes"])


@router.get("", response_model=list[LikeResponse])
def list_likes(user_id: int = Query(...), db: Session = Depends(get_db)):
    repository = LikeRepository(db)
    return repository.get_likes_by_user(user_id)


@router.post("", response_model=LikeResponse, status_code=201)
def add_like(payload: LikeCreate, db: Session = Depends(get_db)):
    repository = LikeRepository(db)
    return repository.add_like(payload)


@router.delete("/{user_id}/{podcast_id}")
def remove_like(user_id: int, podcast_id: int, db: Session = Depends(get_db)):
    repository = LikeRepository(db)
    deleted = repository.remove_like(user_id, podcast_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Like not found")
    return {"ok": True}
