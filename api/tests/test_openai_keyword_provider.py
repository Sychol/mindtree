from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.config import get_settings
from app.models.enums import KeywordCategory, KeywordExtractionMethod
from app.services.keywords.output_parser import parse_keyword_output
from app.services.llm.base import LlmKeywordRequest
from app.services.llm.disabled import DisabledKeywordLlmProvider
from app.services.llm.openai_provider import (
    OpenAIKeywordLlmProvider,
    build_keyword_messages,
)
from app.services.llm.provider import get_keyword_llm_provider


@pytest.fixture(autouse=True)
def clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content),
            )
        ]
    )


class _FakeCompletions:
    def __init__(self, content: str, captured: dict) -> None:
        self._content = content
        self._captured = captured

    def create(self, **kwargs):
        self._captured.update(kwargs)
        return _response(self._content)


class _FakeClient:
    def __init__(self, content: str, captured: dict) -> None:
        self.chat = SimpleNamespace(
            completions=_FakeCompletions(content, captured),
        )


def test_settings_read_keyword_and_summary_models(monkeypatch) -> None:
    monkeypatch.setenv("LLM_KEYWORD_MODEL", "gpt-4.1-nano-test")
    monkeypatch.setenv("LLM_SUMMARY_MODEL", "gpt-4.1-nano-summary")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.keyword_llm_model == "gpt-4.1-nano-test"
    assert settings.summary_llm_model == "gpt-4.1-nano-summary"
    assert settings.has_llm_api_key is True


def test_openai_provider_selected_when_enabled_with_api_key(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_KEYWORD_MODEL", "gpt-4.1-nano-test")
    get_settings.cache_clear()

    provider = get_keyword_llm_provider(get_settings())

    assert isinstance(provider, OpenAIKeywordLlmProvider)
    assert provider.provider_name == "openai"
    assert provider.model == "gpt-4.1-nano-test"


def test_openai_provider_without_api_key_is_disabled(monkeypatch) -> None:
    monkeypatch.setenv("LLM_ENABLED", "true")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "")
    get_settings.cache_clear()

    provider = get_keyword_llm_provider(get_settings())

    assert isinstance(provider, DisabledKeywordLlmProvider)


def test_openai_provider_valid_json_passes_existing_parser(monkeypatch) -> None:
    captured: dict = {}
    raw_output = (
        '{"keywords":[{"text":"rest","normalized":"rest",'
        '"category":"recovery","weight":1.0}]}'
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider._make_openai_client",
        lambda **kwargs: _FakeClient(raw_output, captured),
    )
    provider = OpenAIKeywordLlmProvider(
        api_key="test-key",
        model="gpt-4.1-nano-test",
        timeout_seconds=5,
    )

    result = provider.extract_keywords(
        LlmKeywordRequest(text="need a short rest", source_type="mind_card"),
    )
    candidates = parse_keyword_output(
        result.raw_output,
        extraction_method=KeywordExtractionMethod.LLM.value,
    )

    assert result.provider == "openai:gpt-4.1-nano-test"
    assert captured["model"] == "gpt-4.1-nano-test"
    assert captured["response_format"]["type"] == "json_schema"
    assert candidates[0].normalized == "rest"
    assert candidates[0].category == KeywordCategory.RECOVERY.value
    assert candidates[0].extraction_method == KeywordExtractionMethod.LLM.value


def test_openai_mind_card_mind_signal_candidate_is_allowed(monkeypatch) -> None:
    captured: dict = {}
    raw_output = (
        '{"keywords":[{"text":"tension","normalized":"tension",'
        '"category":"mind_signal","weight":1.0}]}'
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider._make_openai_client",
        lambda **kwargs: _FakeClient(raw_output, captured),
    )
    provider = OpenAIKeywordLlmProvider(
        api_key="test-key",
        model="gpt-4.1-nano-test",
        timeout_seconds=5,
    )

    result = provider.extract_keywords(
        LlmKeywordRequest(text="tight chest", source_type="mind_card"),
    )
    candidates = parse_keyword_output(
        result.raw_output,
        extraction_method=KeywordExtractionMethod.LLM.value,
    )

    assert candidates[0].category == KeywordCategory.MIND_SIGNAL.value


def test_openai_reply_support_recovery_and_coping_candidates_are_allowed(monkeypatch) -> None:
    captured: dict = {}
    raw_output = (
        '{"keywords":['
        '{"text":"support","normalized":"support","category":"support","weight":1.0},'
        '{"text":"rest","normalized":"rest","category":"recovery","weight":0.9},'
        '{"text":"walk","normalized":"walk","category":"coping","weight":0.8}'
        ']}'
    )
    monkeypatch.setattr(
        "app.services.llm.openai_provider._make_openai_client",
        lambda **kwargs: _FakeClient(raw_output, captured),
    )
    provider = OpenAIKeywordLlmProvider(
        api_key="test-key",
        model="gpt-4.1-nano-test",
        timeout_seconds=5,
    )

    result = provider.extract_keywords(
        LlmKeywordRequest(text="take a walk and rest", source_type="reply"),
    )
    candidates = parse_keyword_output(
        result.raw_output,
        extraction_method=KeywordExtractionMethod.LLM.value,
    )

    assert {candidate.category for candidate in candidates} == {
        KeywordCategory.SUPPORT.value,
        KeywordCategory.RECOVERY.value,
        KeywordCategory.COPING.value,
    }


def test_mind_card_prompt_contains_policy_and_mind_signal_instruction() -> None:
    messages = build_keyword_messages(
        LlmKeywordRequest(text="요즘 마음이 답답해요", source_type="mind_card"),
    )
    prompt = "\n".join(message["content"] for message in messages)

    assert "진단하지 않는다" in prompt
    assert "위험도나 자살위험을 판단하지 않는다" in prompt
    assert "공개 여부를 판단하지 않는다" in prompt
    assert "마음신호 키워드" in prompt
    assert "진단명이나 질병명은 사용하지 않는다" in prompt
    assert "mind_signal" in prompt


def test_reply_prompt_contains_support_recovery_and_coping_instruction() -> None:
    messages = build_keyword_messages(
        LlmKeywordRequest(text="잠깐 쉬고 물 한 잔 마셔요", source_type="reply"),
    )
    prompt = "\n".join(message["content"] for message in messages)

    assert "응원" in prompt
    assert "회복" in prompt
    assert "대처법" in prompt
    assert "support" in prompt
    assert "recovery" in prompt
    assert "coping" in prompt
