from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Podcast(Base):
    __tablename__ = "podcasts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    category: Mapped[str] = mapped_column(String(64), default="general", nullable=False)
    event_key: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    content_vector: Mapped[str] = mapped_column(Text, default="")
    audio_url: Mapped[str] = mapped_column(String(500), default="")
    script_path: Mapped[str] = mapped_column(String(500), default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    completion_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
