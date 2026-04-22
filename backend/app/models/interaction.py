from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    podcast_id: Mapped[int] = mapped_column(ForeignKey("podcasts.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    listen_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    progress_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    context_hour: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_weekday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    context_bucket: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
