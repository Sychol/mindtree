import json

from app.services.llm.base import (
    LlmKeywordRequest,
    LlmKeywordResult,
    LlmSummaryRequest,
    LlmSummaryResult,
)


class MockSummaryLlmProvider:
    provider_name = "mock"

    def polish_summary(self, request: LlmSummaryRequest) -> LlmSummaryResult:
        signal_text = " ".join(request.signals[:2]).strip()
        action_text = request.recommended_action or "오늘 가능한 작은 쉼을 하나 선택해 보세요."
        text = (
            "최근 마음 상태를 차분히 살펴보면, "
            f"{signal_text} {action_text}"
        ).strip()
        return LlmSummaryResult(
            text=text,
            provider=self.provider_name,
            used=True,
        )


class MockKeywordLlmProvider:
    provider_name = "mock"

    def extract_keywords(self, request: LlmKeywordRequest) -> LlmKeywordResult:
        text = request.text
        if "잠" in text or "불면" in text:
            keywords = [
                {"text": "잠", "normalized": "잠", "category": "mind_signal", "weight": 1.0},
                {"text": "피로", "normalized": "피로", "category": "mind_signal", "weight": 0.9},
            ]
        elif "답답" in text or "긴장" in text:
            keywords = [
                {"text": "답답함", "normalized": "답답함", "category": "mind_signal", "weight": 1.0},
                {"text": "긴장", "normalized": "긴장", "category": "mind_signal", "weight": 0.9},
            ]
        elif "괜찮" in text or "쉬" in text:
            keywords = [
                {"text": "괜찮아", "normalized": "괜찮아", "category": "support", "weight": 1.0},
                {"text": "쉼", "normalized": "쉼", "category": "recovery", "weight": 0.9},
            ]
        elif "버텨" in text or "버텼" in text:
            keywords = [
                {"text": "버팀", "normalized": "버팀", "category": "mind_signal", "weight": 1.0},
                {"text": "회복", "normalized": "회복", "category": "recovery", "weight": 0.9},
            ]
        elif request.source_type == "reply":
            keywords = [
                {"text": "응원", "normalized": "응원", "category": "support", "weight": 1.0},
                {"text": "위로", "normalized": "위로", "category": "support", "weight": 0.8},
            ]
        else:
            keywords = [
                {"text": "쉼", "normalized": "쉼", "category": "recovery", "weight": 1.0},
            ]

        return LlmKeywordResult(
            raw_output=json.dumps({"keywords": keywords}, ensure_ascii=False),
            provider=self.provider_name,
            used=True,
        )


class FailingMockKeywordLlmProvider:
    provider_name = "mock"

    def extract_keywords(self, request: LlmKeywordRequest) -> LlmKeywordResult:
        del request
        raise RuntimeError("mock keyword provider failed")


class InvalidMockKeywordLlmProvider:
    provider_name = "mock"

    def extract_keywords(self, request: LlmKeywordRequest) -> LlmKeywordResult:
        del request
        return LlmKeywordResult(
            raw_output="not-json",
            provider=self.provider_name,
            used=True,
        )
