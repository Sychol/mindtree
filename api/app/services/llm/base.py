from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LlmSummaryRequest:
    template_text: str
    signals: list[str]
    recommended_action: str | None


@dataclass(frozen=True)
class LlmSummaryResult:
    text: str
    provider: str
    used: bool


@dataclass(frozen=True)
class LlmKeywordRequest:
    text: str
    source_type: str
    source_hint: str | None = None


@dataclass(frozen=True)
class LlmKeywordResult:
    raw_output: str
    provider: str
    used: bool


class SummaryLlmProvider(Protocol):
    provider_name: str

    def polish_summary(self, request: LlmSummaryRequest) -> LlmSummaryResult:
        ...


class KeywordLlmProvider(Protocol):
    provider_name: str

    def extract_keywords(self, request: LlmKeywordRequest) -> LlmKeywordResult:
        ...
