from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import AsyncIterator, Protocol, Union
from urllib import error as urllib_error
from urllib import request as urllib_request

from pydantic_ai import Agent
from pydantic_ai.exceptions import UnexpectedModelBehavior
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

from app.core.config import settings
from app.schemas.generation import ProviderHealthStatus, ScriptModelCapability, ScriptProviderSettings
from app.schemas.script import PodcastScript

logger = logging.getLogger(__name__)


def _is_rate_limit_error(e: Exception) -> bool:
    err_str = str(e).lower()
    return "429" in err_str or "rate_limit" in err_str or "rate limit" in err_str


class ScriptGenerator(Protocol):
    async def generate_script(self, news_content: str, max_retries: int = 3) -> AsyncIterator[PodcastScript]:
        ...


@dataclass(frozen=True)
class ScriptGeneratorDefinition:
    provider: str
    default_models: tuple[str, ...]
    factory: type
    default_base_url: str | None = None

    def capability(self) -> ScriptModelCapability:
        return ScriptModelCapability(
            provider=self.provider,
            available=True,
            models=list(self.default_models),
            reason=None,
        )


class PydanticAIScriptGenerator:
    def __init__(
        self,
        prompt_path: str | Path,
        config: ScriptProviderSettings | None = None,
    ):
        self.prompt_path = Path(prompt_path)
        self.config = config or ScriptProviderSettings(model=settings.script_llm_model)
        self.model = self.config.model or settings.script_llm_model
        self.base_url = (self.config.base_url or os.getenv("OPENAI_BASE_URL") or "").strip()
        self.api_key = (self.config.api_key or os.getenv("OPENAI_API_KEY") or "").strip()
        self._agent = None
        self._json_fallback_agent = None

    def _build_model(self):
        if not self.base_url and not self.api_key:
            return self.model

        provider = OpenAIProvider(
            base_url=self.base_url or None,
            api_key=self.api_key or None,
        )
        model_name = self.model.split(":", 1)[1] if ":" in self.model else self.model
        return OpenAIModel(model_name, provider=provider)

    @property
    def agent(self):
        if self._agent is None:
            with open(self.prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()
            self._agent = Agent(
                model=self._build_model(),
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
                model=self._build_model(),
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
        return PodcastScript.model_validate_json(payload)

    async def _stream_script(self, news_content: str) -> AsyncIterator[PodcastScript]:
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
        except Exception as exc:
            if "tool_choice" not in str(exc):
                raise

            yield await self._generate_script_via_json_fallback(news_content)

    async def generate_script(self, news_content: str, max_retries: int = 5) -> AsyncIterator[PodcastScript]:
        for attempt in range(max_retries):
            try:
                async for script in self._stream_script(news_content):
                    yield script
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
                    raise


class OpenAICompatibleScriptGenerator:
    def __init__(
        self,
        prompt_path: str | Path,
        config: ScriptProviderSettings | None = None,
    ):
        self.prompt_path = Path(prompt_path)
        self.config = config or ScriptProviderSettings(provider="openai_compatible", model=settings.script_llm_model)
        self.provider = self.config.provider
        self.model = self.config.model or settings.script_llm_model
        self.base_url = (self.config.base_url or os.getenv("OPENAI_BASE_URL") or "").strip()
        self.api_key = (self.config.api_key or os.getenv("OPENAI_API_KEY") or "").strip()

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

        if stripped.startswith("{") and stripped.endswith("}"):
            return stripped

        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            return stripped[start:end + 1]
        return stripped

    def _resolve_chat_completions_url(self) -> str:
        if not self.base_url:
            raise RuntimeError(f"{self.provider} provider requires script_llm_base_url")
        normalized = self.base_url.rstrip("/")
        if normalized.endswith("/chat/completions"):
            return normalized
        return normalized + "/chat/completions"

    def _build_request_payload(self, news_content: str) -> dict:
        with open(self.prompt_path, "r", encoding="utf-8") as f:
            base_prompt = f.read()
        schema = json.dumps(PodcastScript.model_json_schema(), ensure_ascii=False, indent=2)
        system_prompt = (
            f"{base_prompt}\n\n"
            "你必须直接输出一个合法 JSON 对象，且只能输出 JSON。"
            "输出必须严格符合下面的 JSON Schema。"
            "不要输出 Markdown 代码块，不要输出解释文字。\n\n"
            f"JSON Schema:\n{schema}"
        )
        return {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": news_content},
            ],
            "temperature": 0.7,
            "response_format": {"type": "json_object"},
        }

    def _parse_response_content(self, body: dict) -> PodcastScript:
        try:
            content = body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"{self.provider} 返回结构异常，缺少 choices[0].message.content") from exc

        payload = self._extract_json_payload(str(content))
        try:
            return PodcastScript.model_validate_json(payload)
        except Exception as exc:
            preview = payload[:400]
            raise RuntimeError(f"{self.provider} 返回了无法解析的脚本 JSON: {preview}") from exc

    def _request_json(self, news_content: str) -> PodcastScript:
        url = self._resolve_chat_completions_url()
        payload = json.dumps(self._build_request_payload(news_content), ensure_ascii=False).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = urllib_request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib_request.urlopen(req, timeout=120) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib_error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")[:400]
            raise RuntimeError(f"{self.provider} 请求失败: HTTP {exc.code} - {error_body}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"{self.provider} 无法连接到脚本服务: {exc.reason}") from exc

        return self._parse_response_content(body)

    async def generate_script(self, news_content: str, max_retries: int = 3) -> AsyncIterator[PodcastScript]:
        import asyncio

        for attempt in range(max_retries):
            try:
                script = await asyncio.to_thread(self._request_json, news_content)
                yield script
                return
            except Exception:
                if attempt < max_retries - 1:
                    await asyncio.sleep((attempt + 1) * 2)
                else:
                    raise


SCRIPT_GENERATOR_REGISTRY: dict[str, ScriptGeneratorDefinition] = {
    "pydantic_ai": ScriptGeneratorDefinition(
        provider="pydantic_ai",
        default_models=(settings.script_llm_model,),
        factory=PydanticAIScriptGenerator,
    ),
    "openai_compatible": ScriptGeneratorDefinition(
        provider="openai_compatible",
        default_models=(settings.script_llm_model,),
        factory=OpenAICompatibleScriptGenerator,
    ),
    "openrouter": ScriptGeneratorDefinition(
        provider="openrouter",
        default_models=(settings.script_llm_model,),
        factory=OpenAICompatibleScriptGenerator,
        default_base_url="https://openrouter.ai/api/v1",
    ),
    "ollama": ScriptGeneratorDefinition(
        provider="ollama",
        default_models=("qwen2.5:14b-instruct",),
        factory=OpenAICompatibleScriptGenerator,
        default_base_url="http://localhost:11434/v1",
    ),
}


def list_script_generator_capabilities() -> list[ScriptModelCapability]:
    return [definition.capability() for definition in SCRIPT_GENERATOR_REGISTRY.values()]


def script_provider_health() -> list[ProviderHealthStatus]:
    results: list[ProviderHealthStatus] = []
    for definition in SCRIPT_GENERATOR_REGISTRY.values():
        if definition.provider == "pydantic_ai":
            results.append(ProviderHealthStatus(provider=definition.provider, ok=True, message="可用；依赖后端 OPENAI_* 环境变量或运行时覆盖"))
        elif definition.provider == "openrouter":
            results.append(ProviderHealthStatus(provider=definition.provider, ok=True, message=f"可用；默认 Base URL 为 {definition.default_base_url}"))
        elif definition.provider == "ollama":
            results.append(ProviderHealthStatus(provider=definition.provider, ok=True, message=f"可用；需要本地服务监听 {definition.default_base_url}"))
        else:
            results.append(ProviderHealthStatus(provider=definition.provider, ok=True, message="可用；需要兼容 OpenAI 的 chat/completions 接口"))
    return results


def create_script_generator(
    prompt_path: str | Path,
    config: ScriptProviderSettings | None = None,
) -> ScriptGenerator:
    resolved = config or ScriptProviderSettings(model=settings.script_llm_model)
    definition = SCRIPT_GENERATOR_REGISTRY.get(resolved.provider)
    if definition is None:
        raise ValueError(f"Unsupported script provider: {resolved.provider}")
    resolved_config = resolved.model_copy(
        update={
            "base_url": resolved.base_url or definition.default_base_url,
            "model": resolved.model or (definition.default_models[0] if definition.default_models else None),
        }
    )
    return definition.factory(prompt_path=prompt_path, config=resolved_config)
