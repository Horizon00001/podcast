import json
from pathlib import Path

import dotenv
from pydantic import BaseModel, Field, model_validator
from pydantic_ai import Agent
from typing import List, Literal, Optional


dotenv.load_dotenv()


class AudioEffect(BaseModel):
    effect_type: Literal["music", "effect", "silence"] = Field(description="效果类型")
    description: str = Field(description="效果描述")
    duration: str = Field(description="持续时间或位置")


class DialogueTurn(BaseModel):
    speaker: Literal["A", "B"] = Field(description="说话者名称，只能是 A 或 B")
    content: str = Field(description="对话内容，需口语化、自然")
    emotion: Optional[str] = Field(default="", description="情感标注")


class PodcastSection(BaseModel):
    section_type: Literal["opening", "transition", "main_content", "closing"] = Field(
        description="段落类型"
    )
    audio_effect: Optional[AudioEffect] = Field(default=None, description="该段落的音频效果")
    dialogues: List[DialogueTurn] = Field(description="该段落的所有对话")
    summary: str = Field(default="", description="内部总结")

    @model_validator(mode="after")
    def validate_alternating_dialogues(self):
        if len(self.dialogues) < 2:
            raise ValueError("每个段落至少需要 2 句对话，并由 A/B 轮流发言。")
        for i in range(1, len(self.dialogues)):
            if self.dialogues[i].speaker == self.dialogues[i - 1].speaker:
                raise ValueError("检测到连续相同说话者，要求 A/B 严格轮流发言。")
        return self


class PodcastScript(BaseModel):
    title: str = Field(description="播客标题")
    intro: str = Field(description="播客简介/导语")
    sections: List[PodcastSection] = Field(description="播客的所有段落")
    total_duration: str = Field(description="预估总时长，如'8分钟'")

    @model_validator(mode="after")
    def validate_both_speakers_present(self):
        speakers = {
            dialogue.speaker for section in self.sections for dialogue in section.dialogues
        }
        if speakers != {"A", "B"}:
            raise ValueError("整篇脚本必须同时包含 A 与 B 两位说话者。")
        return self

    def format_for_output(self) -> str:
        output = []
        output.append(f"标题：{self.title}")
        output.append(f"简介：{self.intro}")
        output.append(f"时长：{self.total_duration}")
        output.append("\n" + "=" * 50 + "\n")

        for i, section in enumerate(self.sections, 1):
            if section.audio_effect:
                effect = section.audio_effect
                output.append(f"[{effect.effect_type.upper()}] {effect.description} ({effect.duration})")

            for dialogue in section.dialogues:
                emotion_tag = f"（{dialogue.emotion}）" if dialogue.emotion else ""
                output.append(f"{dialogue.speaker}：{dialogue.content}{emotion_tag}")

            if i < len(self.sections):
                output.append("")

        return "\n".join(output)


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
                model="openai:deepseek-chat",
                output_type=PodcastScript,
                system_prompt=system_prompt,
            )
        return self._agent

    async def generate_script(self, news_content: str, max_retries: int = 3):
        for attempt in range(max_retries):
            try:
                async with self.agent.run_stream(news_content) as result:
                    async for partial_script in result.stream_output(debounce_by=None):
                        yield partial_script
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
            formatted_output = script.format_for_output()
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(formatted_output)
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)

        return txt_path, json_path
