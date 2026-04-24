"""
集成测试：生成服务
测试任务管理、状态更新、日志记录
"""
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.generation_task import GenerationTask
import app.services.generation_service as generation_service_module
from app.services.generation_service import GenerationService


def _make_test_session_factory(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'generation.sqlite'}")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestGenerationServiceTaskManagement:
    """GenerationService 任务管理集成测试."""

    def test_create_task(self, monkeypatch, tmp_path):
        """测试创建新任务."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = f"test-task-{uuid.uuid4().hex[:8]}"
        task = service.create_task(
            rss_source="default",
            topic="daily-news",
            task_id=task_id,
        )

        assert task.task_id == task_id
        assert task.rss_source == "default"
        assert task.topic == "daily-news"
        assert task.status == "queued"
        assert "已接收生成请求" in task.message

    def test_get_task(self, monkeypatch, tmp_path):
        """测试获取任务."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = str(uuid.uuid4())
        service.create_task("default", "tech", task_id)

        retrieved = service.get_task(task_id)
        assert retrieved is not None
        assert retrieved.task_id == task_id

    def test_get_nonexistent_task(self, monkeypatch, tmp_path):
        """测试获取不存在的任务."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()
        result = service.get_task("nonexistent-id")
        assert result is None

    def test_update_task(self, monkeypatch, tmp_path):
        """测试更新任务状态."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = str(uuid.uuid4())
        service.create_task("default", "news", task_id)

        service._update_task(task_id, "running", "Processing RSS feeds...")

        task = service.get_task(task_id)
        assert task.status == "running"
        assert task.message == "Processing RSS feeds..."

    def test_update_task_to_succeeded(self, monkeypatch, tmp_path):
        """测试更新任务为成功状态."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = str(uuid.uuid4())
        service.create_task("default", "news", task_id)

        service._update_task(task_id, "succeeded", "Generation completed successfully!")

        task = service.get_task(task_id)
        assert task.status == "succeeded"
        assert task.message == "Generation completed successfully!"

    def test_update_task_to_failed(self, monkeypatch, tmp_path):
        """测试更新任务为失败状态."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = str(uuid.uuid4())
        service.create_task("default", "news", task_id)

        service._update_task(task_id, "failed", "Error: RSS feed not found")

        task = service.get_task(task_id)
        assert task.status == "failed"
        assert "Error" in task.message


class TestGenerationServiceLogging:
    """GenerationService 日志记录集成测试."""

    def test_add_log(self, monkeypatch, tmp_path):
        """测试添加日志."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = str(uuid.uuid4())
        service.create_task("default", "news", task_id)

        service.add_log(task_id, "Starting pipeline...")
        service.add_log(task_id, "Fetching RSS feeds...")

        logs = service.get_new_logs(task_id, 0)

        assert len(logs) == 2
        assert "Starting pipeline" in logs[0]
        assert "Fetching RSS feeds" in logs[1]

    def test_get_new_logs_respects_offset(self, monkeypatch, tmp_path):
        """测试 get_new_logs 正确处理偏移量."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = str(uuid.uuid4())
        service.create_task("default", "news", task_id)

        service.add_log(task_id, "Log 1")
        service.add_log(task_id, "Log 2")
        service.add_log(task_id, "Log 3")

        # 获取从偏移量 1 开始的日志
        logs = service.get_new_logs(task_id, 1)

        assert len(logs) == 2
        assert "Log 1" not in logs[0]  # Log 1 应该被跳过
        assert "Log 2" in logs[0]

    def test_get_new_logs_empty_when_no_new(self, monkeypatch, tmp_path):
        """测试没有新日志时返回空列表."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()

        task_id = str(uuid.uuid4())
        service.create_task("default", "news", task_id)

        service.add_log(task_id, "Only log")

        # 获取所有日志
        logs1 = service.get_new_logs(task_id, 0)
        assert len(logs1) == 1

        # 再获取一次，没有新日志
        logs2 = service.get_new_logs(task_id, len(logs1))
        assert len(logs2) == 0


class TestGenerationTaskModel:
    """GenerationTask 模型测试."""

    def test_task_has_timestamps(self, monkeypatch, tmp_path):
        """测试任务包含时间戳."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()
        task_id = str(uuid.uuid4())

        task = service.create_task("default", "news", task_id)

        assert task.created_at is not None
        assert task.updated_at is not None
        assert abs((task.updated_at - task.created_at).total_seconds()) < 1

    def test_task_updated_at_changes(self, monkeypatch, tmp_path):
        """测试更新任务时 updated_at 改变."""
        monkeypatch.setattr(generation_service_module, "SessionLocal", _make_test_session_factory(tmp_path))
        service = GenerationService()
        task_id = str(uuid.uuid4())

        task = service.create_task("default", "news", task_id)
        original_updated = task.updated_at

        # 等待一小段时间确保时间戳差异
        import time
        time.sleep(0.01)

        service._update_task(task_id, "running", "Running...")

        updated_task = service.get_task(task_id)
        assert updated_task.updated_at >= original_updated


class TestGenerationServiceRunPipeline:
    """GenerationService.run_pipeline 直接调用测试."""

    def test_run_pipeline_direct_call(self, monkeypatch):
        """测试 run_pipeline 被直接调用而非通过子进程."""
        from app.pipelines import podcast_pipeline

        captured = {}

        async def fake_run_pipeline(topic=None, log_callback=None):
            captured["topic"] = topic
            captured["log_callback"] = log_callback
            log_callback("test log output")

        monkeypatch.setattr(podcast_pipeline, "run_pipeline", fake_run_pipeline)

        async def _run():
            await podcast_pipeline.run_pipeline(topic="tech", log_callback=lambda msg: captured.setdefault("logs", []).append(msg))

        asyncio.run(_run())

        assert captured["topic"] == "tech"
        assert captured["log_callback"] is not None
        assert "test log output" in captured.get("logs", [])

    def test_run_pipeline_default_log_callback(self, monkeypatch):
        """测试 run_pipeline 默认使用 print 作为日志回调."""
        from app.pipelines.podcast_pipeline import run_pipeline
        import inspect

        sig = inspect.signature(run_pipeline)
        params = sig.parameters
        assert "log_callback" in params
        assert params["log_callback"].default == print

    def test_generation_service_calls_run_pipeline_directly(self, monkeypatch, tmp_path):
        """测试 GenerationService 直接调用 run_pipeline 而非子进程."""
        from app.services import generation_service as gs_module
        from app.services.generation_service import GenerationService

        monkeypatch.setattr(gs_module, "SessionLocal", _make_test_session_factory(tmp_path))

        captured = {}

        async def fake_run_pipeline(topic=None, log_callback=None):
            captured["topic"] = topic
            captured["log_callback"] = log_callback
            log_callback("pipeline step 1")
            log_callback("pipeline step 2")

        monkeypatch.setattr(gs_module, "run_pipeline", fake_run_pipeline)

        service = GenerationService()
        task_id = "test-task-direct"
        service.create_task("default", "tech", task_id)

        async def _run():
            await service.run_pipeline(task_id)

        asyncio.run(_run())

        assert captured["topic"] == "tech"
        assert captured["log_callback"] is not None

        updated_task = service.get_task(task_id)
        assert updated_task.status == "succeeded"

    def test_generation_service_handles_pipeline_error(self, monkeypatch, tmp_path):
        """测试直接调用时 pipeline 异常能被正确处理."""
        from app.services import generation_service as gs_module
        from app.services.generation_service import GenerationService

        monkeypatch.setattr(gs_module, "SessionLocal", _make_test_session_factory(tmp_path))

        async def fake_failing_pipeline(topic=None, log_callback=None):
            log_callback("starting pipeline...")
            raise ValueError("RSS feed not available")

        monkeypatch.setattr(gs_module, "run_pipeline", fake_failing_pipeline)

        service = GenerationService()
        task_id = "test-task-failing"
        service.create_task("default", "tech", task_id)

        async def _run():
            await service.run_pipeline(task_id)

        asyncio.run(_run())

        updated_task = service.get_task(task_id)
        assert updated_task.status == "failed"
        assert "RSS feed not available" in updated_task.message
