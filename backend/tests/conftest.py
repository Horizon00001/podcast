import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app import models  # noqa: F401 - ensures all models are imported


# Force the entire pytest process onto an isolated SQLite file before any
# test imports `app.main`, which would otherwise bootstrap the default
# `podcast.db` database.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="podcast-pytest-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/podcast_test.db"


@pytest.fixture
def db_session():
    """Provides an in-memory SQLite session for tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # Import all models to register them with Base
    from app.models import user, podcast, interaction  # noqa: F401

    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(engine)
