import asyncio
import json
import logging
from pathlib import Path
from typing import Awaitable, Callable

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.core.config import settings
from app.schemas.script import AudioEffect, DialogueTurn, PodcastScript, PodcastSection

logger = logging.getLogger(__name__)


def _is_rate_limit_error(e: Exception) -> bool:
    err_str = str(e).lower()
    return "429" in err_str or "rate_limit" in err_str or "rate limit" in err_str


class ScriptService:
    TRANSITION_SUMMARY = "承接上一段重点，并自然引出下一个分析问题。"

    def __init__(self, project_root: str | Path, output_dir: str | Path):
        self.project_root = Path(project_root)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.prompt_path = self.project_root / "prompt.txt"
        self._agent = None
        self._json_fallback_agent = None

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

    @property
    def json_fallback_agent(self):
        if self._json_fallback_agent is None:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                base_prompt = f.read()
            schema = json.dumps(PodcastScript.model_json_schema(), ensure_ascii=False, indent=2)
            fallback_prompt = (
                f"{base_prompt}\n\n"
                "你必须直接输出一个合法 JSON 对象，且只能输出 JSON，本次不要使用工具调用或函数调用。"
                "输出必须严格符合下面的 JSON Schema。"
                "不要输出 Markdown 代码块，不要输出解释文字。\n\n"
                f"JSON Schema:\n{schema}"
            )
            self._json_fallback_agent = Agent(
                model=settings.script_llm_model,
                system_prompt=fallback_prompt,
            )
        return self._json_fallback_agent

    @staticmethod
    def _extract_json_payload(content: str) -> str:
        stripped = content.strip()
        if stripped.startswith("```"):
            lines = stripped.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            stripped = "\n".join(lines).strip()
        return stripped

    async def _generate_script_via_json_fallback(self, news_content: str) -> PodcastScript:
        result = await self.json_fallback_agent.run(news_content)
        payload = self._extract_json_payload(str(result.output))
        return self._normalize_script( PodcastScript.model_validate_json(payload))

    @classmethod
    def _build_transition_section(cls) -> PodcastSection:
        return PodcastSection(
            section_type="transition",
            dialogues=[
                DialogueTurn(
                    speaker="A",
                    content="刚才这条线索先放在这里，我们把镜头转到另一个同样关键的变化上。",
                    emotion="自然承接",
                ),
                DialogueTurn(
                    speaker="B",
                    content="因为只有把这两个信号放在一起看，前面那个判断到底站不站得住，才会更清楚。",
                    emotion="简洁分析",
                ),
            ],
            summary=cls.TRANSITION_SUMMARY,
        )

    @classmethod
    def _normalize_script(cls, script: PodcastScript) -> PodcastScript:
        normalized_script = script
        if not any(section.section_type == "transition" for section in script.sections):
            normalized_sections: list[PodcastSection] = []
            main_content_seen = 0
            insert_after_first_main = sum(section.section_type == "main_content" for section in script.sections) > 1

            for section in script.sections:
                normalized_sections.append(section)
                if section.section_type != "main_content":
                    continue

                main_content_seen += 1
                if insert_after_first_main and main_content_seen == 1:
                    normalized_sections.append(cls._build_transition_section())

            normalized_script = script.model_copy(update={"sections": normalized_sections})

        return normalized_script.model_copy(update={"total_duration": normalized_script.estimate_duration()})

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
            yield self._normalize_script(final_result.output)
        except Exception as exc:
            if "tool_choice" not in str(exc):
                raise

            yield await self._generate_script_via_json_fallback(news_content)

    async def generate_script(self, news_content: str, max_retries: int = 5):
        for attempt in range(max_retries):
            try:
                async for script in self._stream_script(news_content):
                    yield self._normalize_script(script)
                return
            except Exception as e:
                is_rate_limit = _is_rate_limit_error(e)
                if is_rate_limit:
                    wait_time = min(2 ** attempt, 30)
                    logger.warning(f"429 Rate limit detected, waiting {wait_time}s before retry ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                elif attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(f"Script generation failed: {e}, retrying in {wait_time}s ({attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Script generation failed after {max_retries} attempts: {e}")
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
        script = ScriptService._normalize_script(script)
        formatted_output = script.format_for_output()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(formatted_output)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)
