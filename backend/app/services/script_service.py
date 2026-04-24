import json
from pathlib import Path
from typing import Awaitable, Callable

import dotenv
from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.core.config import settings
from app.schemas.script import PodcastScript


dotenv.load_dotenv()


class ScriptService:
    def __init__(self, project_root: str | Path, output_dir: str | Path):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_path = self.project_root / "prompt.txt"
        self._agent = None

    @property
    def agent(self):
        if self._agent is None:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            self._agent = Agent(
                model=settings.script_llm_model,
                output_type=PodcastScript,
                system_prompt=system_prompt,
            )
        return self._agent

    async def _stream_script(self, news_content: str):
        """Prefer streaming output, then fall back to a blocking run if needed."""
        try:
            async with self.agent.run_stream(news_content) as result:
                latest_script = None
                async for partial_script in result.stream_output(debounce_by=None):
                    latest_script = partial_script
                    yield partial_script

                if latest_script is None:
                    raise RuntimeError("脚本生成失败：未收到任何有效输出")
                return
        except UnexpectedModelBehavior:
            final_result = await self.agent.run(news_content)
            yield final_result.output

    async def generate_script(self, news_content: str, max_retries: int = 3):
        for attempt in range(max_retries):

            try:
                async for script in self._stream_script(news_content):
                    yield script
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep((attempt + 1) * 2)
                else:
                    raise e

    async def generate_and_save(self, news_content: str) -> tuple[Path, Path]:
        txt_path = self.output_dir / "podcast_script.txt"
        json_path = self.output_dir / "podcast_script.json"
        final_script = None

        async for script in self.generate_script(news_content):
            final_script = script
            self._write_script_files(script, txt_path, json_path)

        return txt_path, json_path

    async def generate_and_save_streaming_sections(
        self,
        news_content: str,
        on_section_ready: Callable[[int, dict, bool], Awaitable[None]] | None = None,
    ) -> tuple[Path, Path]:
        txt_path = self.output_dir / "podcast_script.txt"
        json_path = self.output_dir / "podcast_script.json"
        final_script = None
        flushed_sections = 0

        async for script in self.generate_script(news_content):
            final_script = script
            self._write_script_files(script, txt_path, json_path)

            if on_section_ready is None:
                continue

            # Once a new section appears, the previous one is stable enough to start TTS.
            while flushed_sections + 1 < len(script.sections):
                await on_section_ready(
                    flushed_sections,
                    script.sections[flushed_sections].model_dump(),
                    True,
                )
                flushed_sections += 1

        if final_script is None:
            raise RuntimeError("脚本生成失败：未收到任何有效输出")

        if on_section_ready is not None:
            while flushed_sections < len(final_script.sections):
                await on_section_ready(
                    flushed_sections,
                    final_script.sections[flushed_sections].model_dump(),
                    flushed_sections < len(final_script.sections) - 1,
                )
                flushed_sections += 1

        return txt_path, json_path

    @staticmethod
    def _write_script_files(script: PodcastScript, txt_path: Path, json_path: Path) -> None:
        formatted_output = script.format_for_output()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(formatted_output)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)
