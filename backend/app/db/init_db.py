from app.db.base import Base
from app.db.migrations import run_migrations
from app.db.session import engine


def initialize_schema() -> None:
    from app import models
    from app.models.generation_task import GenerationTask

    _ = models
    _ = GenerationTask
    Base.metadata.create_all(bind=engine)


def apply_migrations() -> None:
    run_migrations()


def init_db() -> None:
    """Backward-compatible bootstrap used by existing tests and callers."""
    initialize_schema()
    apply_migrations()
