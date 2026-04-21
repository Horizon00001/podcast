from sqlalchemy import inspect, text

from app.db.session import engine


def run_migrations() -> None:
    _ensure_podcasts_category_column()
    _ensure_generation_tasks_table()


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


def _ensure_generation_tasks_table() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    if "generation_tasks" in table_names:
        return

    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE generation_tasks ("
                "task_id VARCHAR(64) PRIMARY KEY, "
                "status VARCHAR(32) NOT NULL, "
                "message TEXT NOT NULL DEFAULT '', "
                "rss_source VARCHAR(128) NOT NULL DEFAULT 'default', "
                "topic VARCHAR(128) NOT NULL DEFAULT 'daily-news', "
                "logs TEXT NOT NULL DEFAULT '[]', "
                "created_at DATETIME NOT NULL, "
                "updated_at DATETIME NOT NULL"
                ")"
            )
        )
