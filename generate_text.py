"""
播客 Prompt 脚本生成工具（超详尽说明）
================

概览
- 目标：将原始新闻内容自动转化为结构化的「播客对话脚本」，并在生成过程中进行“流式”更新与落盘。
- 技术栈：Pydantic（数据模型）、pydantic-ai（Agent/流式推理）、DeepSeek（兼容 OpenAI API 的推理模型）、python-dotenv（环境变量）。
- 输出：人类可读的文本（txt）与结构化 JSON（json），统一保存在 output 目录。

核心流程
1. 声明严谨的层次化数据结构（PodcastScript -> PodcastSection -> DialogueTurn + AudioEffect），确保 AI 输出可验证、可解析。
2. 加载系统提示词（prompt.txt），设定 Agent 的角色与输出规范，降低“模型自由度”导致的格式偏差。
3. 创建 pydantic-ai Agent，绑定输出类型（PodcastScript），让推理结果直接转为强类型对象。
4. 以“流式”方式调用模型：每获取到新的片段就立刻产出，边生成边写入文件，实现近实时反馈。

设计动机与关键点
- 强类型：通过 Pydantic 定义数据模型，确保字段完整性、类型正确（对流式场景尤为重要，便于部分结果的校验）。
- 流式生成：减少“等待完整结果”的时延；便于实时展示生成进度/中间内容；对用户体验更友好。
- 重试与容错：在复杂网络/推理场景下，可能出现 JSON 解析或连接问题；设计了有限重试与指数退避（线性增加）的等待。
- 易用输出：同时输出 txt 与 json，兼顾人类阅读与程序消费；txt 使用合适的符号标记（如 Emoji）提升可读性。

使用前置
- 环境变量：需在 .env 中放置必要的 API Key（例如 DeepSeek 的兼容 OpenAI API Key），通过 python-dotenv 自动加载。
- prompt.txt：用于描述播客生成行为规范（角色设定、风格、格式），请确保文件存在且内容清晰。

快速上手
1. 在项目根目录创建并填写 .env（例如：OPENAI_API_KEY=xxx）。
2. 编写/完善 prompt.txt（例如定义“开场/过渡/主要内容/结尾”等段落生成规则）。
3. 运行本文件：python generate_text.py（或在 IDE 中直接执行）。
4. 观察控制台的“流式”输出与 output 目录中的实时文件变更。

文件与目录约定
- output/podcast_script.txt：供人阅读的完整脚本（会在流式过程中不断覆盖更新）。
- output/podcast_script.json：结构化数据（Pydantic 的 dict 序列化，便于二次处理）。

常见问题（FAQ）
- 为什么要强类型？避免模型返回格式漂移，便于校验与后续处理。
- 如果流式输出中断？会进行有限重试；最终失败将抛出异常，便于外层监控/报警。
- 是否支持多段新闻合并？当前示例以单段输入演示，扩展思路：在数据模型中增加“来源列表”或“多主题分节”。
"""

# ============ 标准库导入 ============
# os：与操作系统交互（此处主要用于环境变量读取与路径相关操作的备用方案）。
# json：将 Pydantic 模型转为字典后序列化为 JSON 文件。
# asyncio：驱动异步流式推理；主入口使用 asyncio.run 启动。
# pathlib.Path：更优雅的路径操作与目录创建。
import os
import json
import asyncio
from pathlib import Path

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ============ 第三方库导入 ============
# python-dotenv（dotenv）：从 .env 文件加载环境变量，便于本地开发与部署环境隔离。
# pydantic：声明式数据模型与字段校验；Field 提供描述与默认值。
# typing：类型注解（List、Literal、Optional），提高可读性与维护性。
# pydantic_ai.Agent：与模型交互的高级封装，支持结果自动解析与流式输出。
import dotenv
from pydantic import BaseModel, Field, ValidationError, model_validator
from typing import List, Literal, Optional
from pydantic_ai import Agent

from episode_planner import EpisodePlan, format_plan_for_prompt

# ============ 环境变量加载 ============
# 目的：在运行之前将 .env 中定义的密钥/配置注入进程环境（os.environ），避免把密钥写死在代码中。
# 注意：不要在日志中打印真实密钥；此处仅提示加载是否完成。
print(">>> 正在加载环境变量...")
dotenv.load_dotenv()
print(">>> 环境变量加载完成")


# ============================================================
# 数据模型定义
# ============================================================
# 使用 Pydantic 定义播客脚本的层次化数据结构
# 层级关系：PodcastScript -> PodcastSection -> DialogueTurn + AudioEffect

class AudioEffect(BaseModel):
    """
    音频效果模型
    
    描述播客中使用的音效元素，如背景音乐、音效等。
    
    属性：
        effect_type: 效果类型，只能是 "music"（音乐）、"effect"（音效）或 "silence"（静音/停顿）
        description: 对效果的文字描述，用于生成时指定具体内容
        duration: 效果的持续时间或出现位置，如 "30秒" 或 "开场"

    使用示例：
        - 开场音乐：
            effect_type = "music"
            description = "轻快的电子开场曲，音量中等"
            duration = "开场"
        - 过渡音效：
            effect_type = "effect"
            description = "纸张翻动声，短促"
            duration = "段落切换"
        - 强调停顿：
            effect_type = "silence"
            description = "1秒安静以突出下一句"
            duration = "强调前"

    设计提示：
        - 语义尽量具体（“轻快”“中等音量”“短促”等），有助于后续 TTS/混音系统精确渲染。
        - duration 可以是时间或语境位置（“开场”“段落切换”“结尾”），便于脚本排布。
    """
    effect_type: Literal["music", "effect", "silence"] = Field(description="效果类型")
    description: str = Field(description="效果描述")
    duration: str = Field(description="持续时间或位置")


class DialogueTurn(BaseModel):
    """
    对话轮次模型
    
    表示播客中单次说话的内容。
    
    属性：
        speaker: 说话者标识，如"A"、"B"等（可扩展为姓名或角色名）
        content: 具体的对话内容，需要是口语化、自然的表达
        emotion: 可选的情感标注，用于控制语气或表达方式（如“兴奋”“认真”“轻松”）

    使用示例：
        speaker = "A"
        content = "今天我们聊聊最新的 AI 模型更新。"
        emotion = "好奇"

    设计提示：
        - content 应避免过分书面化，强调“可读即可说”的口语风格。
        - emotion 为空时不展示，减少信息噪声；有值时作为“演绎提示”供配音参考。
    """
    speaker: Literal["A", "B"] = Field(description="说话者名称，只能是 A 或 B")
    content: str = Field(description="对话内容，需口语化、自然")
    emotion: Optional[str] = Field(default="", description="情感标注")


class PodcastSection(BaseModel):
    """
    播客段落模型
    
    播客脚本被划分为多个段落，每个段落包含对话和可选的音频效果。
    
    属性：
        section_type: 段落类型，决定该段在播客中的位置和功能：
            - "opening": 开场白
            - "transition": 过渡段落
            - "main_content": 主要内容
            - "closing": 结尾总结
        audio_effect: 该段落使用的音频效果（可选）
        dialogues: 该段落中的所有对话轮次列表
        summary: 内部总结，用于 AI 生成时的参考（不输出给用户）

    使用示例：
        section_type = "opening"
        audio_effect = AudioEffect(...)
        dialogues = [DialogueTurn(...), DialogueTurn(...)]
        summary = "本段介绍节目的主题与背景。"

    设计提示：
        - 将“功能语义”与“表现语义”分离：section_type 决定结构位置；audio_effect/summary 服务表现与生成质量。
        - 对话条目尽量短促、自然；避免长段文本影响节奏。
    """
    section_type: Literal["opening", "transition", "main_content", "closing"] = Field(description="段落类型")
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
    """
    播客脚本根模型
    
    这是 AI Agent 最终输出的数据结构，包含完整的播客脚本信息。
    
    属性：
        title: 播客节目的标题
        intro: 简介/导语部分，吸引听众的开场介绍
        sections: 播客的所有段落列表，按播放顺序排列
        total_duration: 预估的总时长，如"8分钟"

    设计提示：
        - 标题应简洁且信息密度高；intro 提供情境与价值引导。
        - total_duration 只是估计值，真实播出时长受配音速度与音效时长影响。
    """
    title: str = Field(description="播客标题")
    intro: str = Field(description="播客简介/导语")
    sections: List[PodcastSection] = Field(description="播客的所有段落")
    total_duration: str = Field(description="预估总时长，如'8分钟'")

    @model_validator(mode="after")
    def validate_both_speakers_present(self):
        speakers = {dialogue.speaker for section in self.sections for dialogue in section.dialogues}
        if speakers != {"A", "B"}:
            raise ValueError("整篇脚本必须同时包含 A 与 B 两位说话者。")
        return self

    def format_for_output(self) -> str:
        """
        将播客脚本格式化为易读的文本输出
        
        转换步骤：
        1. 输出标题、简介和时长信息
        2. 遍历每个段落，输出音频效果（如果有）
        3. 输出段落中的所有对话，附带情感标注
        4. 段落之间添加空行分隔
        
        返回：
            格式化的文本字符串，可直接打印或保存

        设计细节：
        - 使用列表累积字符串片段，最终一次性 join，避免多次拼接的性能损耗。
        - 对音频效果进行显式标记 [MUSIC]/[EFFECT]/[SILENCE]，便于后续系统解析或人工审阅。
        - emotion 为空时不显示，减少视觉负担；有值时以括号形式紧随内容，保持简洁。
        - 段落之间以空行分隔，提升可读性（最后一段后不额外加空行）。
        """
        output = []
        # 输出元信息部分
        output.append(f"🎙️ 标题：{self.title}")
        output.append(f"📝 简介：{self.intro}")
        output.append(f"⏱️ 时长：{self.total_duration}")
        output.append("\n" + "="*50 + "\n")
        
        # 遍历每个段落进行处理
        for i, section in enumerate(self.sections, 1):
            # 如果段落有音频效果，先输出效果信息
            if section.audio_effect:
                effect = section.audio_effect
                output.append(f"[{effect.effect_type.upper()}] {effect.description} ({effect.duration})")
            
            # 输出该段落中的所有对话
            for dialogue in section.dialogues:
                emotion_tag = f"（{dialogue.emotion}）" if dialogue.emotion else ""
                output.append(f"{dialogue.speaker}：{dialogue.content}{emotion_tag}")
            
            # 在段落之间添加空行（最后一个段落后不加）
            if i < len(self.sections):
                output.append("")
        
        # 将列表合并为单个字符串返回
        return "\n".join(output)


# ============================================================
# Agent 配置
# ============================================================

# 从 prompt.txt 文件读取系统提示词
# 系统提示词定义了 AI Agent 的角色、生成规则和输出格式要求
# 注意：
# - 文件必须存在且编码为 UTF-8；
# - 内容应明确输出类型、字段要求、风格与长度约束；
# - 可在提示词中对“段落类型”“音效用法”“情感标注”进行具体约束，显著提升一致性。
print(">>> 正在读取系统提示词（prompt.txt）...")
with open("prompt.txt", "r", encoding="utf-8") as f:
    system_prompt = f.read()
print(f">>> 系统提示词读取完成，长度：{len(system_prompt)} 字符")

# 创建 pydantic-ai Agent 实例
# Agent 是 AI 与代码之间的接口，负责：
# 1. 接收用户输入（新闻内容）
# 2. 根据系统提示词生成响应
# 3. 将响应解析为指定的 PodcastScript 数据结构
print(">>> 正在创建 AI Agent...")
agent = Agent(
    model='openai:deepseek-chat',   # 使用 DeepSeek 的 OpenAI 兼容接口；形式为 "openai:模型名"
    output_type=PodcastScript,      # 新版 pydantic_ai 可能使用 result_type，旧版为 output_type；此处与环境版本保持一致
    system_prompt=system_prompt,    # 传入系统提示词，定义生成规则与结构约束
)
print(">>> AI Agent 创建完成")


# ============================================================
# 核心功能函数
# ============================================================

def load_rss_news(rss_data_path: Path) -> str:
    """
    从 rss_data.json 中读取并格式化新闻内容
    """
    if not rss_data_path.exists():
        print(f">>> 警告：找不到 {rss_data_path}，将使用空内容。")
        return ""
    
    try:
        with open(rss_data_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        formatted_news = []
        import re
        for feed in data:
            for entry in feed.get('entries', []):
                item_lines = []
                title = (entry.get('title') or "").strip()
                if title:
                    item_lines.append(f"标题: {title}")
                summary = entry.get('summary')
                if summary:
                    cleaned_summary = re.sub('<[^<]+?>', '', summary).strip()
                    if cleaned_summary:
                        item_lines.append(f"摘要: {cleaned_summary[:200]}...")
                if item_lines:
                    formatted_news.extend(item_lines)
                    formatted_news.append("")
        
        return "\n".join(formatted_news)
    except Exception as e:
        print(f">>> 读取 RSS 数据失败: {e}")
        return ""


def load_episode_plan(episode_plan_path: Path) -> Optional[EpisodePlan]:
    if not episode_plan_path.exists():
        return None

    try:
        with open(episode_plan_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return EpisodePlan(
            topic_id=raw["topic_id"],
            topic_name=raw["topic_name"],
            title_hint=raw["title_hint"],
            theme_statement=raw["theme_statement"],
            audience=raw["audience"],
            editorial_angle=raw["editorial_angle"],
            selected_items=[],
            segments=[],
            closing_takeaway=raw["closing_takeaway"],
        )
    except Exception as e:
        print(f">>> 警告：读取节目计划失败，将回退到原始新闻内容模式: {e}")
        return None


def build_generation_input(topic: str, rss_data_path: Path, episode_plan_path: Optional[Path] = None) -> str:
    if episode_plan_path:
        try:
            with open(episode_plan_path, "r", encoding="utf-8") as f:
                raw_plan = json.load(f)
            plan = EpisodePlan(
                topic_id=raw_plan["topic_id"],
                topic_name=raw_plan["topic_name"],
                title_hint=raw_plan["title_hint"],
                theme_statement=raw_plan["theme_statement"],
                audience=raw_plan["audience"],
                editorial_angle=raw_plan["editorial_angle"],
                selected_items=[],
                segments=[],
                closing_takeaway=raw_plan["closing_takeaway"],
            )
            plan.selected_items = [
                type("SelectedItem", (), item)() for item in raw_plan.get("selected_items", [])
            ]
            plan.segments = [
                type("Segment", (), segment)() for segment in raw_plan.get("segments", [])
            ]
            return format_plan_for_prompt(plan)
        except Exception as e:
            print(f">>> 警告：节目计划格式化失败，将回退到原始新闻内容模式: {e}")

    news_content = load_rss_news(rss_data_path)
    if not news_content:
        return ""
    return f"节目主题: {topic}\n请围绕这个主题组织本期节目，而不是逐条罗列新闻。\n\n原始新闻池:\n{news_content}"


def _load_plan_from_path(episode_plan_path: Path) -> Optional[EpisodePlan]:
    return load_episode_plan(episode_plan_path)


def _resolve_output_dir(output_dir: Optional[Path], episode_plan_path: Optional[Path]) -> Path:
    if output_dir:
        return Path(output_dir)
    if episode_plan_path:
        return Path(episode_plan_path).parent
    return Path("output")

async def generate_podcast_script(news_content: str, max_retries: int = 3):
    """
    生成播客脚本（流式输出异步生成器）
    
    将新闻内容转换为结构化的播客对话脚本，并流式产生中间状态。
    
    参数：
        news_content: 要转换的新闻内容
        max_retries: 最大重试次数
        
    产出 (Yields):
        PodcastScript: 当前接收到的部分脚本对象

    行为与约束：
        - 使用 agent.run_stream(news_content) 进行流式推理；
        - 任何时刻接收到的部分结果都必须可被 Pydantic 解析（可能是“增量完善”，但结构不破坏）。
        - 捕获 ValidationError 以及通用 Exception，避免一次失败导致整体中断。

    重试策略：
        - 最多重试 max_retries 次；
        - 每次失败后等待 (attempt + 1) * 2 秒（线性退避），兼顾响应性与保护。
        - 仅在最终失败时抛出异常，让上层主流程得知错误并进行告警/处理。

    常见错误：
        - json_invalid：模型在流式过程中产出未闭合或格式不全的 JSON（可通过提示词强化与重试缓解）。
        - 网络/配额问题：请检查 API Key 与网络状态；在 .env 中正确配置密钥。
    """
    print(">>> 开始调用 AI 模型生成播客脚本...")
    print(f">>> 输入内容长度：{len(news_content)} 字符")
    print(">>> 正在生成播客脚本中...")
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                print(f"\n>>> 正在进行第 {attempt + 1} 次重试...")
            
            async with agent.run_stream(news_content) as result:
                chunk_count = 0
                async for partial_script in result.stream_output(debounce_by=None):
                    chunk_count += 1
                    yield partial_script
                
                if chunk_count <= 1:
                    print(">>> 提示：本次模型返回为单次完整结果，未产生可见增量片段。")
                print("\n>>> AI 模型调用完成")
                return
        except (ValidationError, Exception) as e:
            print(f"\n>>> 第 {attempt + 1} 次尝试失败: {type(e).__name__}")
            if "json_invalid" in str(e).lower():
                print(f">>> 错误详情：检测到 JSON 解析错误，这通常是由于模型输出的流式数据不完整导致的。")
            
            if attempt < max_retries - 1:
                await asyncio.sleep((attempt + 1) * 2)
            else:
                raise e


# ============================================================
# 主程序入口
# ============================================================

async def main(
    topic: str = "daily-news",
    episode_plan_path: Optional[Path] = None,
    rss_data_path: Optional[Path] = None,
    output_dir: Optional[Path] = None,
):
    """
    程序主函数
    """
    # 初始化 output 目录
    output_dir = _resolve_output_dir(output_dir, episode_plan_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    rss_data_path = rss_data_path or (output_dir / "rss_data.json")
    episode_plan_path = episode_plan_path or (output_dir / "episode_plan.json")
    
    # 从节目编排计划或 rss_data.json 加载生成输入
    print(f">>> 正在准备主题化节目输入，topic={topic} ...")
    news_content = build_generation_input(topic, rss_data_path, episode_plan_path)
    
    if not news_content:
        print(">>> 错误：未获取到有效的新闻内容，请先运行 rss_fetch.py")
        return
    
    print("\n" + "="*50)
    print(">>> 播客Prompt脚本生成工具已启动")
    print("="*50)
    print(f"\n>>> 成功从 RSS 加载了 {len(news_content)} 字符的新闻内容。")
    print("\n开始生成播客脚本（若模型支持增量输出将实时显示）...")
    print("-" * 50)
    
    partial_count = 0
    final_script = None

    txt_path = output_dir / "podcast_script.txt"
    json_path = output_dir / "podcast_script.json"

    # 使用 async for 迭代生成器，实现流式输出效果
    async for script in generate_podcast_script(news_content):
        partial_count += 1
        final_script = script
        
        # 每产生一部分内容就更新一次文件（覆盖写）
        formatted_output = script.format_for_output()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(formatted_output)
        with open(json_path, "w", encoding="utf-8") as f:
            # 兼容 Pydantic v2 的模型转 dict
            json.dump(script.model_dump(), f, ensure_ascii=False, indent=2)

    # 最终输出完整的格式化结果
    if final_script:
        if partial_count <= 1:
            print(">>> 说明：输出文件是实时写入的，但这次 API 仅返回一次完整结构，因此终端看起来不是逐句流式。")
        print("\n" + "="*50)
        print(">>> 生成完成！最终完整脚本：")
        formatted_output = final_script.format_for_output()
        print(formatted_output)
        print(f"\n>>> 脚本已实时保存至：{txt_path}")
        print(f">>> 结构化数据已实时保存至：{json_path}")
    
    print("\n" + "-" * 50)
    print("播客脚本生成完成！")


# 程序入口：只有直接运行此文件时才执行 main()
# 导入作为模块使用时不会自动执行
if __name__ == "__main__":
    asyncio.run(main())
