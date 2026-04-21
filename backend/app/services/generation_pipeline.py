import asyncio
import os
import sys
from pathlib import Path
from typing import Awaitable, Callable

from app.core.config import settings


class GenerationPipelineRunner:
    def __init__(self, project_root: Path, output_dir: Path):
        self.project_root = project_root
        self.output_dir = output_dir

    async def run(self, topic: str, add_log: Callable[[str], Awaitable[None]]) -> Path:
        env = os.environ.copy()
        backend_dir = settings.backend_dir

        await add_log("=" * 50)
        await add_log("🚀 开始执行播客生成全流程")
        await add_log("=" * 50)
        await add_log("\n启动后端 CLI 流水线")

        process = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            "-m",
            settings.pipeline_module,
            "run-pipeline",
            "--topic",
            topic,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(backend_dir),
            env=env,
        )

        while True:
            chunk = await process.stdout.read(1024)
            if not chunk:
                break

            text = chunk.decode("utf-8", errors="replace")
            await add_log(text)

        await process.wait()
        if process.returncode != 0:
            raise RuntimeError(f"执行失败，退出码: {process.returncode}")

        podcast_file = self.output_dir / "audio" / "podcast_full.mp3"
        await add_log("\n" + "=" * 50)
        await add_log("✅ 全流程执行完成")
        await add_log(f"📁 音频文件: {podcast_file}")
        await add_log("=" * 50)
        return podcast_file
