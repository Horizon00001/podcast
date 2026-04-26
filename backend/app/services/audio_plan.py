from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional


RenderItemType = Literal["speech", "silence", "music", "effect"]


@dataclass(slots=True)
class RenderPlanItem:
    item_type: RenderItemType
    text: Optional[str] = None
    asset_path: Optional[Path] = None
    voice: Optional[str] = None
    style: Optional[str] = None
    duration_ms: Optional[int] = None
    trim_start_ms: Optional[int] = None
    trim_end_ms: Optional[int] = None
    volume: Optional[float] = None
    fade_out_ms: Optional[int] = None
    speaker: Optional[str] = None
    metadata: dict = field(default_factory=dict)


@dataclass(slots=True)
class RenderPlan:
    title: str
    items: list[RenderPlanItem] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class RenderPlanner:
    """Convert the script model into a renderable audio timeline."""

    VOICE_MAP = {
        "主持人A": "male",
        "主持人B": "female",
        "A": "male",
        "B": "female",
    }

    DEFAULT_VOICE = "female"

    SECTION_GAPS_MS = {
        "opening": 350,
        "transition": 650,
        "main_content": 420,
        "closing": 900,
    }

    @classmethod
    def build_from_script(cls, script_data: dict, force_trailing_gap: bool = False) -> RenderPlan:
        title = script_data.get("title", "podcast")
        plan = RenderPlan(title=title)
        sections = script_data.get("sections", [])

        for section_index, section in enumerate(sections):
            section_type = section.get("section_type", "main_content")
            section_effect = section.get("audio_effect")

            if section_type == "opening":
                plan.items.extend(cls._build_opening_cues(section_effect))
            elif section_type == "transition":
                plan.items.extend(cls._build_transition_cues(section_effect))
            elif section_type == "closing":
                plan.items.extend(cls._build_closing_prefix_cues(section_effect))
            elif section_effect:
                plan.items.append(cls._build_generic_effect_item(section_type, section_effect))

            for dialogue in section.get("dialogues", []):
                speaker = dialogue.get("speaker")
                plan.items.append(
                    RenderPlanItem(
                        item_type="speech",
                        text=dialogue.get("content", ""),
                        voice=cls.VOICE_MAP.get(speaker, cls.DEFAULT_VOICE),
                        style=section_type,
                        speaker=speaker,
                        metadata={
                            "section_type": section_type,
                            "emotion": dialogue.get("emotion", ""),
                        },
                    )
                )

            if section_type == "closing":
                plan.items.extend(cls._build_closing_suffix_cues(section_effect))

            should_add_gap = section_index < len(sections) - 1
            if force_trailing_gap and section_index == len(sections) - 1:
                should_add_gap = True

            if should_add_gap:
                gap_ms = cls.SECTION_GAPS_MS.get(section_type, 400)
                if section_type == "closing":
                    gap_ms = max(gap_ms, 1200)
                plan.items.append(
                    RenderPlanItem(
                        item_type="silence",
                        duration_ms=gap_ms,
                        metadata={"section_type": section_type},
                    )
                )

        return plan

    @classmethod
    def _build_opening_cues(cls, section_effect: dict | None) -> list[RenderPlanItem]:
        items: list[RenderPlanItem] = []
        duration_ms = cls._parse_duration_to_ms((section_effect or {}).get("duration", "")) or 10000
        items.append(
            RenderPlanItem(
                item_type="music",
                duration_ms=min(max(duration_ms, 7000), 12000),
                trim_start_ms=0,
                metadata={
                    "section_type": "opening",
                    "role": "opening_theme",
                    "description": (section_effect or {}).get("description", ""),
                    "duration_label": (section_effect or {}).get("duration", ""),
                },
            )
        )
        items.append(
            RenderPlanItem(
                item_type="silence",
                duration_ms=420,
                metadata={"section_type": "opening", "position": "open_to_voice"},
            )
        )
        return items

    @classmethod
    def _build_transition_cues(cls, section_effect: dict | None) -> list[RenderPlanItem]:
        items: list[RenderPlanItem] = []
        if section_effect and section_effect.get("effect_type") != "music":
            items.append(cls._build_generic_effect_item("transition", section_effect))

        items.append(
            RenderPlanItem(
                item_type="music",
                duration_ms=2400,
                trim_start_ms=8000,
                metadata={
                    "section_type": "transition",
                    "role": "transition_sting",
                    "description": "短促转场音乐提示",
                },
            )
        )
        items.append(
            RenderPlanItem(
                item_type="silence",
                duration_ms=180,
                metadata={"section_type": "transition", "position": "sting_to_voice"},
            )
        )
        return items

    @classmethod
    def _build_closing_prefix_cues(cls, section_effect: dict | None) -> list[RenderPlanItem]:
        items: list[RenderPlanItem] = []
        if section_effect and section_effect.get("effect_type") != "music":
            items.append(cls._build_generic_effect_item("closing", section_effect))
        return items

    @classmethod
    def _build_closing_suffix_cues(cls, section_effect: dict | None) -> list[RenderPlanItem]:
        if not section_effect or section_effect.get("effect_type") != "music":
            return []

        duration_ms = cls._parse_duration_to_ms(section_effect.get("duration", "")) or 9000
        return [
            RenderPlanItem(
                item_type="silence",
                duration_ms=350,
                metadata={"section_type": "closing", "position": "voice_to_tail"},
            ),
            RenderPlanItem(
                item_type="music",
                duration_ms=min(max(duration_ms, 7000), 12000),
                trim_end_ms=min(max(duration_ms, 7000), 12000),
                metadata={
                    "section_type": "closing",
                    "role": "closing_tail",
                    "description": section_effect.get("description", ""),
                    "duration_label": section_effect.get("duration", ""),
                },
            ),
        ]

    @classmethod
    def _build_generic_effect_item(cls, section_type: str, section_effect: dict) -> RenderPlanItem:
        effect_type = section_effect.get("effect_type", "effect")
        duration_ms = cls._parse_duration_to_ms(section_effect.get("duration", ""))
        return RenderPlanItem(
            item_type=effect_type if effect_type in {"music", "effect", "silence"} else "effect",
            duration_ms=duration_ms,
            metadata={
                "section_type": section_type,
                "description": section_effect.get("description", ""),
                "duration_label": section_effect.get("duration", ""),
            },
        )

    @staticmethod
    def _parse_duration_to_ms(value: str) -> int:
        if not value:
            return 0

        text = str(value).strip().lower()
        match = re.search(r"(\d+(?:\.\d+)?)\s*(ms|毫秒|秒|s|min|分钟|分)?", text)
        if not match:
            return 0

        amount = float(match.group(1))
        unit = match.group(2) or "ms"

        if unit in {"ms", "毫秒"}:
            return int(amount)
        if unit in {"s", "秒"}:
            return int(amount * 1000)
        if unit in {"min", "分钟", "分"}:
            return int(amount * 60 * 1000)
        return int(amount)
