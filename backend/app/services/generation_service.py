import asyncio
from pathlib import Path

from app.core.config import settings
from app.db.session import SessionLocal
from app.repositories.generation_task_repository import GenerationTaskRepository
from app.services.generation_pipeline import GenerationPipelineRunner
from app.services.generation_result_service import GenerationResultService


class GenerationService:
    def __init__(self):
        self.project_root = settings.project_root
        self.config_path = settings.feed_config_path
        self.output_dir = settings.output_dir
        self.pipeline_runner = GenerationPipelineRunner(self.project_root, self.output_dir)
        self.result_service = GenerationResultService(self.output_dir)
        self._session_factory = SessionLocal

    def _repository(self) -> GenerationTaskRepository:
        return GenerationTaskRepository(self._session_factory())

    def _with_repository(self, action):
        db = self._session_factory()
        try:
            return action(GenerationTaskRepository(db))
        finally:
            db.close()

    def create_task(self, rss_source: str, topic: str, task_id: str):
        return self._with_repository(
            lambda repository: repository.create(
                task_id=task_id,
                rss_source=rss_source,
                topic=topic,
                status="queued",
                message=f"已接收生成请求: rss_source={rss_source}, topic={topic}",
            )
        )

    async def _add_log(self, task_id: str, log_message: str):
        self._with_repository(lambda repository: repository.append_log(task_id, log_message))

    async def run_pipeline(self, task_id: str):
        task = self.get_task(task_id)
        if not task:
            return

        self._update_task(task_id, "running", f"正在按主题生成节目: {task.topic}")
        
        try:
            podcast_file = await self.pipeline_runner.run(
                task.topic,
                lambda message: self._add_log(task_id, message),
            )
            await self.result_service.save_generated_podcast(task_id, self._add_log)
            
            self._update_task(task_id, "succeeded", f"播客生成完成，文件: {podcast_file}")
             
        except Exception as exc:
            error_message = str(exc)
            if error_message.startswith("执行失败，退出码:"):
                await self._add_log(task_id, f"❌ {error_message}")
                self._update_task(task_id, "failed", error_message)
                return

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
