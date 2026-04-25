import asyncio
import json
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.pipelines.podcast_pipeline import run_pipeline
from app.repositories.generation_task_repository import GenerationTaskRepository
from app.schemas.user import UserPreferences


class GenerationService:
    def __init__(self):
        self.project_root = settings.project_root
        self.config_path = settings.feed_config_path
        self.output_dir = settings.output_dir
        self._session_factory = SessionLocal

    def _repository(self) -> GenerationTaskRepository:
        return GenerationTaskRepository(self._session_factory())

    def _with_repository(self, action):
        db = self._session_factory()
        try:
            return action(GenerationTaskRepository(db))
        finally:
            db.close()

    def create_task(
        self,
        rss_source: str,
        topic: str,
        task_id: str,
        user_id: int | None = None,
        use_subscriptions: bool = False,
        custom_rss: list[dict] | None = None,
    ):
        metadata = {
            "text": f"已接收生成请求: rss_source={rss_source}, topic={topic}",
            "user_id": user_id,
            "use_subscriptions": use_subscriptions,
            "custom_rss": custom_rss or [],
        }
        return self._with_repository(
            lambda repository: repository.create(
                task_id=task_id,
                rss_source=rss_source,
                topic=topic,
                status="queued",
                message=json.dumps(metadata, ensure_ascii=False),
            )
        )

    def _task_metadata(self, task) -> dict:
        try:
            payload = json.loads(task.message or "{}")
            return payload if isinstance(payload, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    def _load_user_preferences(self, user_id: int | None) -> UserPreferences:
        if user_id is None:
            return UserPreferences()

        from app.models.user import User

        def load(repository: GenerationTaskRepository):
            user = repository.db.query(User).filter(User.id == user_id).first()
            if not user or not user.preferences:
                return UserPreferences()
            try:
                return UserPreferences.model_validate(json.loads(user.preferences))
            except (json.JSONDecodeError, ValueError, TypeError):
                return UserPreferences()

        return self._with_repository(load)

    def _resolve_sources(self, task) -> tuple[list[str] | None, list[dict]]:
        metadata = self._task_metadata(task)
        use_subscriptions = bool(metadata.get("use_subscriptions"))
        extra_feeds = list(metadata.get("custom_rss") or [])

        if use_subscriptions:
            preferences = self._load_user_preferences(metadata.get("user_id"))
            selected = list(preferences.subscription.rss_sources)
            extra_feeds.extend(feed.model_dump() for feed in preferences.subscription.custom_rss)
            selected.extend(feed.get("id") for feed in extra_feeds if feed.get("id"))
            return selected, extra_feeds

        if task.rss_source and task.rss_source not in ("default", "all", "subscribed"):
            return [task.rss_source], extra_feeds

        return None, extra_feeds

    async def _add_log(self, task_id: str, log_message: str):
        self._with_repository(lambda repository: repository.append_log(task_id, log_message))

    def cancel_task(self, task_id: str):
        task = self.get_task(task_id)
        if not task:
            return False
        if task.status in ("succeeded", "failed", "cancelled"):
            return False
        self._update_task(task_id, "cancelled", "任务已取消")
        return True

    def _check_cancelled(self, task_id: str) -> bool:
        task = self.get_task(task_id)
        return task is not None and task.status == "cancelled"

    async def run_pipeline(self, task_id: str):
        task = self.get_task(task_id)
        if not task:
            return

        check_cancelled = lambda: self._check_cancelled(task_id)

        self._update_task(task_id, "running", f"正在按主题生成节目: {task.topic}")

        try:
            selected_source_ids, extra_feeds = self._resolve_sources(task)
            await run_pipeline(
                topic=task.topic,
                selected_source_ids=selected_source_ids,
                extra_feeds=extra_feeds,
                log_callback=lambda message: asyncio.create_task(self._add_log(task_id, message)),
                check_cancelled=check_cancelled,
            )
            self._update_task(task_id, "succeeded", "播客生成完成")

        except asyncio.CancelledError:
            await self._add_log(task_id, "任务已被用户取消")
            self._update_task(task_id, "cancelled", "任务已取消")
        except Exception as exc:
            if self._check_cancelled(task_id):
                await self._add_log(task_id, "任务已被用户取消")
                self._update_task(task_id, "cancelled", "任务已取消")
            else:
                error_message = str(exc)
                await self._add_log(task_id, f"❌ 任务执行异常: {error_message}")
                self._update_task(task_id, "failed", f"任务执行异常: {exc}")

    def run_task(self, task_id: str):
        asyncio.run(self.run_pipeline(task_id))

    def get_new_logs(self, task_id: str, last_count: int) -> list:
        return self._with_repository(lambda repository: repository.get_logs(task_id))[last_count:]

    def get_task(self, task_id: str):
        return self._with_repository(lambda repository: repository.get(task_id))

    def get_task_logs(self, task_id: str) -> list[str]:
        return self._with_repository(lambda repository: repository.get_logs(task_id))

    def add_log(self, task_id: str, message: str) -> None:
        self._with_repository(lambda repository: repository.append_log(task_id, message))

    def _update_task(self, task_id: str, status: str, message: str):
        self._with_repository(lambda repository: repository.update(task_id, status=status, message=message))


generation_service = GenerationService()
