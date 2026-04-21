import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.generation_task import GenerationTask


class GenerationTaskRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        task_id: str,
        rss_source: str,
        topic: str,
        status: str,
        message: str,
    ) -> GenerationTask:
        task = GenerationTask(
            task_id=task_id,
            rss_source=rss_source,
            topic=topic,
            status=status,
            message=message,
            logs=json.dumps([], ensure_ascii=False),
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get(self, task_id: str) -> GenerationTask | None:
        return self.db.query(GenerationTask).filter(GenerationTask.task_id == task_id).first()

    def update(self, task_id: str, **fields) -> GenerationTask | None:
        task = self.get(task_id)
        if not task:
            return None

        for key, value in fields.items():
            if hasattr(task, key):
                setattr(task, key, value)

        task.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(task)
        return task

    def append_log(self, task_id: str, message: str) -> GenerationTask | None:
        task = self.get(task_id)
        if not task:
            return None

        logs = json.loads(task.logs or "[]")
        logs.append(message)
        task.logs = json.dumps(logs, ensure_ascii=False)
        task.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_logs(self, task_id: str) -> list[str]:
        task = self.get(task_id)
        if not task:
            return []
        return json.loads(task.logs or "[]")
