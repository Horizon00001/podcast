import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic_ai.exceptions import UnexpectedModelBehavior

from app.schemas.generation import ScriptProviderSettings
from app.schemas.script import DialogueTurn, PodcastScript, PodcastSection
from app.services.script_generator import OpenAICompatibleScriptGenerator, PydanticAIScriptGenerator, create_script_generator, list_script_generator_capabilities


def _make_script() -> PodcastScript:
    return PodcastScript(
        title="Test Podcast",
        intro="Intro",
        sections=[
            PodcastSection(
                section_type="opening",
                dialogues=[
                    DialogueTurn(speaker="A", content="Hello"),
                    DialogueTurn(speaker="B", content="Hi"),
                ],
            ),
            PodcastSection(
                section_type="main_content",
                dialogues=[
                    DialogueTurn(speaker="A", content="Hello"),
                    DialogueTurn(speaker="B", content="Hi"),
                ],
            ),
            PodcastSection(
                section_type="closing",
                dialogues=[
                    DialogueTurn(speaker="A", content="Bye"),
                    DialogueTurn(speaker="B", content="See you"),
                ],
            ),
        ],
        total_duration="5分钟",
    )


def _make_stream_ctx(scripts: list[PodcastScript]):
    class _Ctx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def stream_output(self, debounce_by=None):
            for script in scripts:
                yield script

    return _Ctx()


def test_create_script_generator_returns_pydantic_ai(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("test prompt", encoding="utf-8")

    generator = create_script_generator(prompt_file, ScriptProviderSettings(model="openai:test-model"))

    assert isinstance(generator, PydanticAIScriptGenerator)
    assert generator.model == "openai:test-model"


def test_create_script_generator_rejects_unknown_provider(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("test prompt", encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported script provider"):
        create_script_generator(prompt_file, ScriptProviderSettings(provider="unknown"))


def test_create_script_generator_supports_openai_compatible(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("test prompt", encoding="utf-8")

    generator = create_script_generator(
        prompt_file,
        ScriptProviderSettings(provider="openai_compatible", model="gpt-test", base_url="https://example.com/v1"),
    )

    assert isinstance(generator, OpenAICompatibleScriptGenerator)


def test_create_script_generator_supports_openrouter_defaults(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("test prompt", encoding="utf-8")

    generator = create_script_generator(
        prompt_file,
        ScriptProviderSettings(provider="openrouter", model=None, base_url=None),
    )

    assert isinstance(generator, OpenAICompatibleScriptGenerator)
    assert generator.base_url == "https://openrouter.ai/api/v1"


def test_create_script_generator_supports_ollama_defaults(tmp_path):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("test prompt", encoding="utf-8")

    generator = create_script_generator(
        prompt_file,
        ScriptProviderSettings(provider="ollama", model=None, base_url=None),
    )

    assert isinstance(generator, OpenAICompatibleScriptGenerator)
    assert generator.base_url == "http://localhost:11434/v1"
    assert generator.model == "qwen2.5:14b-instruct"


def test_pydantic_ai_script_generator_streams_results(tmp_path, monkeypatch):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("test prompt", encoding="utf-8")
    generator = PydanticAIScriptGenerator(prompt_file, ScriptProviderSettings(model="openai:test-model"))
    script = _make_script()

    mock_agent = MagicMock()
    mock_agent.run_stream = MagicMock(return_value=_make_stream_ctx([script]))
    generator._agent = mock_agent

    async def collect():
        results = []
        async for item in generator.generate_script("news"):
            results.append(item)
        return results

    results = asyncio.run(collect())
    assert len(results) == 1
    assert results[0].title == "Test Podcast"


def test_pydantic_ai_script_generator_falls_back_to_run(tmp_path, monkeypatch):
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("test prompt", encoding="utf-8")
    generator = PydanticAIScriptGenerator(prompt_file, ScriptProviderSettings(model="openai:test-model"))
    script = _make_script()

    class _FailingCtx:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        def stream_output(self, debounce_by=None):
            async def _raise():
                raise UnexpectedModelBehavior("stream failed")
                yield

            return _raise()

    mock_agent = MagicMock()
    mock_agent.run_stream = MagicMock(return_value=_FailingCtx())
    mock_agent.run = AsyncMock(return_value=MagicMock(output=script))
    generator._agent = mock_agent

    async def collect():
        results = []
        async for item in generator.generate_script("news"):
            results.append(item)
        return results

    results = asyncio.run(collect())
    assert len(results) == 1
    assert results[0].title == "Test Podcast"
    assert mock_agent.run.called


def test_list_script_generator_capabilities_contains_pydantic_ai():
    capabilities = list_script_generator_capabilities()

    assert any(item.provider == "pydantic_ai" for item in capabilities)
    assert any(item.provider == "openai_compatible" for item in capabilities)
    assert any(item.provider == "openrouter" for item in capabilities)
    assert any(item.provider == "ollama" for item in capabilities)


def test_openai_compatible_extract_json_payload_handles_wrapped_text():
    payload = OpenAICompatibleScriptGenerator._extract_json_payload(
        "Here is your JSON:\n```json\n{\"title\":\"T\"}\n```\nThanks"
    )

    assert payload == '{"title":"T"}'
