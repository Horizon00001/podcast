from app.db.base import Base
from app.db.migrations import run_migrations
from app.db.session import engine


def init_db() -> None:
    from app import models

    _ = models
    Base.metadata.create_all(bind=engine)
    run_migrations()
