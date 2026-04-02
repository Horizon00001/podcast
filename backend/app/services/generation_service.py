import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock

from app.services.rss_service import RSSService
from app.services.script_service import ScriptService
from app.services.tts_service import TTSService


@dataclass
class GenerationTask:
    task_id: str
    status: str
    message: str
    created_at: datetime
    updated_at: datetime
    rss_source: str
    topic: str


class GenerationService:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[3]
        self.config_path = self.project_root / "config" / "feed.json"
        self.output_dir = self.project_root / "output"
        self._tasks: dict[str, GenerationTask] = {}
        self._lock = Lock()

    def create_task(self, rss_source: str, topic: str, task_id: str) -> GenerationTask:
        now = datetime.now(UTC)
        task = GenerationTask(
            task_id=task_id,
            status="queued",
            message=f"已接收生成请求: rss_source={rss_source}, topic={topic}",
            created_at=now,
            updated_at=now,
            rss_source=rss_source,
            topic=topic,
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> GenerationTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    async def run_pipeline(self, task_id: str):
        self._update_task(task_id, "running", "正在抓取 RSS 数据")
        try:
            rss_service = RSSService(self.config_path, self.output_dir)
            rss_path = rss_service.fetch_and_save()

            self._update_task(task_id, "running", "正在生成播客脚本")
            script_service = ScriptService(self.project_root, self.output_dir)
            news_content = rss_service.load_rss_news(rss_path)
            if not news_content:
                self._update_task(task_id, "failed", "RSS 数据为空，请检查 feed.json 配置")
                return
            script_json_path = self.output_dir / "podcast_script.json"
            await script_service.generate_and_save(news_content)

            self._update_task(task_id, "running", "正在合成播客音频")
            tts_service = TTSService(self.output_dir)
            await tts_service.synthesize_podcast(script_json_path)

            self._update_task(task_id, "succeeded", "播客生成任务执行完成")
        except Exception as exc:
            self._update_task(task_id, "failed", f"任务执行异常: {exc}")

    def run_task(self, task_id: str):
        asyncio.run(self.run_pipeline(task_id))

    def _update_task(self, task_id: str, status: str, message: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.status = status
            task.message = message
            task.updated_at = datetime.now(UTC)


generation_service = GenerationService()
