from app.core.config import Settings
from app.services.llm.base import KeywordLlmProvider, SummaryLlmProvider
from app.services.llm.disabled import DisabledKeywordLlmProvider, DisabledSummaryLlmProvider
from app.services.llm.mock import (
    FailingMockKeywordLlmProvider,
    InvalidMockKeywordLlmProvider,
    MockKeywordLlmProvider,
    MockSummaryLlmProvider,
)
from app.services.llm.openai_provider import OpenAIKeywordLlmProvider


def get_summary_llm_provider(settings: Settings) -> SummaryLlmProvider:
    provider = settings.llm_provider.strip().lower()
    if not settings.llm_enabled or provider in {"", "disabled", "none"}:
        return DisabledSummaryLlmProvider()
    if provider == "mock":
        return MockSummaryLlmProvider()

    # Live providers are intentionally left out of Phase 06. The participant
    # flow must keep working without a real external LLM integration.
    return DisabledSummaryLlmProvider()


def get_keyword_llm_provider(settings: Settings) -> KeywordLlmProvider:
    provider = settings.llm_provider.strip().lower()
    if not settings.llm_enabled or provider in {"", "disabled", "none"}:
        return DisabledKeywordLlmProvider()
    if provider == "mock":
        return MockKeywordLlmProvider()
    if provider == "mock_failure":
        return FailingMockKeywordLlmProvider()
    if provider == "mock_invalid":
        return InvalidMockKeywordLlmProvider()
    if provider in {"openai", "gpt", "gpt_nano"}:
        if not settings.has_llm_api_key:
            return DisabledKeywordLlmProvider()
        return OpenAIKeywordLlmProvider(
            api_key=settings.llm_api_key,
            model=settings.keyword_llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    return DisabledKeywordLlmProvider()
