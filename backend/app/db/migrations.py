from sqlalchemy import inspect, text

from app.db.session import engine


def run_migrations() -> None:
    _ensure_podcasts_category_column()


def _ensure_podcasts_category_column() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "podcasts" not in table_names:
        return

    columns = {column["name"] for column in inspector.get_columns("podcasts")}
    if "category" in columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE podcasts "
                "ADD COLUMN category VARCHAR(64) NOT NULL DEFAULT 'general'"
            )
        )
