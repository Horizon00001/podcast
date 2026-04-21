import asyncio
import os
import sys
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Optional, Callable, Awaitable, Dict, List

from app.services.podcast_service import PodcastService
from app.schemas.podcast import PodcastCreate
from app.db.session import SessionLocal


@dataclass
class GenerationTask:
    task_id: str
    status: str
    message: str
    created_at: datetime
    updated_at: datetime
    rss_source: str
    topic: str
    logs: List[str] = field(default_factory=list)
    _log_callback: Optional[Callable[[str], Awaitable[None]]] = field(default=None, repr=False)


class GenerationService:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parents[3]
        self.config_path = self.project_root / "config" / "feed.json"
        self.output_dir = self.project_root / "output"
        self._tasks: Dict[str, GenerationTask] = {}
        self._lock = Lock()

    def create_task(self, rss_source: str, topic: str, task_id: str) -> GenerationTask:
        now = datetime.now(timezone.utc)
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

    def get_task(self, task_id: str) -> Optional[GenerationTask]:
        with self._lock:
            return self._tasks.get(task_id)

    async def _add_log(self, task_id: str, log_message: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if task:
                task.logs.append(log_message)

    async def _save_to_database(self, task_id: str):
        """将生成的结果保存到数据库"""
        try:
            json_path = self.output_dir / "podcast_script.json"
            audio_path = self.output_dir / "audio" / "podcast_full.mp3"
            
            if not json_path.exists() or not audio_path.exists():
                await self._add_log(task_id, "⚠️ 未能找到生成的文件，入库失败")
                return

            # 读取元数据
            with open(json_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)
            
            title = script_data.get("title", "未命名播客")
            summary = script_data.get("intro", "")
            
            # 复制文件以保证唯一性
            final_audio_name = f"podcast_{task_id}.mp3"
            final_audio_path = self.output_dir / "audio" / final_audio_name
            import shutil
            shutil.copy2(audio_path, final_audio_path)
            
            # 复制脚本文件（可选）
            final_script_name = f"podcast_{task_id}.json"
            final_script_path = self.output_dir / "audio" / final_script_name
            shutil.copy2(json_path, final_script_path)

            # 调用服务入库
            db = SessionLocal()
            try:
                podcast_service = PodcastService(db)
                payload = PodcastCreate(
                    title=title,
                    summary=summary,
                    audio_url=f"/audio/{final_audio_name}",
                    script_path=str(final_script_path)
                )
                podcast = podcast_service.create_podcast(payload)
                await self._add_log(task_id, f"✅ 播客已成功添加到列表: ID={podcast.id}")
            finally:
                db.close()
                
        except Exception as e:
            await self._add_log(task_id, f"❌ 入库过程中出现错误: {str(e)}")

    async def run_pipeline(self, task_id: str):
        task = self.get_task(task_id)
        if not task:
            return

        self._update_task(task_id, "running", f"正在按主题生成节目: {task.topic}")
        
        try:
            main_py = self.project_root / "main.py"
            env = os.environ.copy()
            
            await self._add_log(task_id, "=" * 50)
            await self._add_log(task_id, "🚀 开始执行播客生成全流程")
            await self._add_log(task_id, "=" * 50)
            
            await self._add_log(task_id, "\n[1/3] 抓取 RSS 数据")
            
            process = await asyncio.create_subprocess_exec(
                 sys.executable,
                  "-u",  # 禁用缓冲，确保实时输出
                  str(main_py),
                  "--topic",
                  task.topic,
                  stdout=asyncio.subprocess.PIPE,
                  stderr=asyncio.subprocess.STDOUT,
                  cwd=str(self.project_root),
                 env=env,
             )
            
            # 改进读取逻辑：使用块读取以支持 end=" " 的实时效果
            buffer = ""
            while True:
                # 读取一小块内容，而不是等待一整行
                chunk = await process.stdout.read(1024)
                if not chunk:
                    break
                
                text = chunk.decode("utf-8", errors="replace")
                buffer += text
                
                # 如果有内容，立即推送到日志中
                # 我们不再简单地按行切分，而是直接把这块文本发出去
                await self._add_log(task_id, text)
            
            await process.wait()
            
            if process.returncode != 0:
                await self._add_log(task_id, f"❌ 执行失败，退出码: {process.returncode}")
                self._update_task(task_id, "failed", f"执行失败，退出码: {process.returncode}")
                return
            
            audio_dir = self.output_dir / "audio"
            podcast_file = audio_dir / "podcast_full.mp3"
            
            await self._add_log(task_id, "\n" + "=" * 50)
            await self._add_log(task_id, "✅ 全流程执行完成")
            await self._add_log(task_id, f"📁 音频文件: {podcast_file}")
            await self._add_log(task_id, "=" * 50)
            
            # 入库逻辑
            await self._save_to_database(task_id)
            
            self._update_task(task_id, "succeeded", f"播客生成完成，文件: {podcast_file}")
            
        except Exception as exc:
            await self._add_log(task_id, f"❌ 任务执行异常: {str(exc)}")
            self._update_task(task_id, "failed", f"任务执行异常: {exc}")

    def run_task(self, task_id: str):
        asyncio.run(self.run_pipeline(task_id))

    def get_new_logs(self, task_id: str, last_count: int) -> list:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return []
            return task.logs[last_count:]

    def _update_task(self, task_id: str, status: str, message: str):
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            task.status = status
            task.message = message
            task.updated_at = datetime.now(timezone.utc)


generation_service = GenerationService()
