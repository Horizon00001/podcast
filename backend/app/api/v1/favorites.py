from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.favorite_repository import FavoriteRepository
from app.schemas.favorite import FavoriteCreate, FavoriteResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("", response_model=list[FavoriteResponse])
def list_favorites(user_id: int = Query(...), db: Session = Depends(get_db)):
    repository = FavoriteRepository(db)
    return repository.get_favorites_by_user(user_id)


@router.post("", response_model=FavoriteResponse, status_code=201)
def add_favorite(payload: FavoriteCreate, db: Session = Depends(get_db)):
    repository = FavoriteRepository(db)
    return repository.add_favorite(payload)


@router.delete("/{user_id}/{podcast_id}")
def remove_favorite(user_id: int, podcast_id: int, db: Session = Depends(get_db)):
    repository = FavoriteRepository(db)
    deleted = repository.remove_favorite(user_id, podcast_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Favorite not found")
    return {"ok": True}
