from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class AudioEffect(BaseModel):
    effect_type: Literal["music", "effect", "silence"] = Field(description="效果类型")
    description: str = Field(description="效果描述")
    duration: str = Field(description="持续时间或位置")


class DialogueTurn(BaseModel):
    speaker: Literal["A", "B"] = Field(description="说话者名称，只能是 A 或 B")
    content: str = Field(description="对话内容，需口语化、自然，并具备适合音频收听的节奏感")
    emotion: Optional[str] = Field(default="", description="情感标注")


class PodcastSection(BaseModel):
    section_type: Literal["opening", "transition", "main_content", "closing"] = Field(
        description="段落类型，分别承担开场立题、承上启下、主体推进、结尾收束的节目职责"
    )
    audio_effect: Optional[AudioEffect] = Field(default=None, description="该段落的音频效果")
    dialogues: List[DialogueTurn] = Field(description="该段落的所有对话，需体现 A 主播与 B 分析师的分工")
    summary: str = Field(default="", description="内部总结，说明该段完成的节目功能与听众应带走的重点")

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
    intro: str = Field(description="播客简介/导语，需快速说明本期主题、价值和讨论路径")
    sections: List[PodcastSection] = Field(description="播客的所有段落，整体需形成可听的节目编排结构")
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
