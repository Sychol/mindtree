from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass

from app.core.config import Settings
from app.models.enums import KeywordExtractionMethod
from app.services.keywords.output_parser import KeywordOutputParseError, parse_keyword_output
from app.services.keywords.types import KeywordCandidate
from app.services.llm.base import LlmKeywordRequest
from app.services.llm.provider import get_keyword_llm_provider


class KeywordLlmUnavailable(RuntimeError):
    pass


class KeywordLlmFailed(RuntimeError):
    pass


@dataclass(frozen=True)
class KeywordLlmExtractionResult:
    candidates: list[KeywordCandidate]
    provider: str
    raw_keyword_count: int


def extract_keywords_with_llm(
    *,
    settings: Settings,
    text: str,
    source_type: str,
    source_hint: str | None = None,
) -> KeywordLlmExtractionResult:
    provider = get_keyword_llm_provider(settings)
    if provider.provider_name == "disabled":
        raise KeywordLlmUnavailable("LLM disabled")

    request = LlmKeywordRequest(
        text=text,
        source_type=source_type,
        source_hint=source_hint,
    )
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(provider.extract_keywords, request)
    try:
        result = future.result(timeout=max(settings.llm_timeout_seconds, 1))
    except TimeoutError as exc:
        future.cancel()
        raise KeywordLlmFailed("LLM timeout") from exc
    except Exception as exc:
        raise KeywordLlmFailed("LLM keyword extraction failed") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)

    if not result.used:
        raise KeywordLlmUnavailable("LLM disabled")

    try:
        candidates = parse_keyword_output(
            result.raw_output,
            extraction_method=KeywordExtractionMethod.LLM.value,
        )
    except KeywordOutputParseError as exc:
        raise KeywordLlmFailed("LLM schema parse failed") from exc

    return KeywordLlmExtractionResult(
        candidates=candidates,
        provider=result.provider,
        raw_keyword_count=len(candidates),
    )
