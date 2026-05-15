from app.services.llm.base import LlmKeywordRequest, LlmKeywordResult, LlmSummaryRequest, LlmSummaryResult


class DisabledSummaryLlmProvider:
    provider_name = "disabled"

    def polish_summary(self, request: LlmSummaryRequest) -> LlmSummaryResult:
        return LlmSummaryResult(
            text=request.template_text,
            provider=self.provider_name,
            used=False,
        )


class DisabledKeywordLlmProvider:
    provider_name = "disabled"

    def extract_keywords(self, request: LlmKeywordRequest) -> LlmKeywordResult:
        del request
        return LlmKeywordResult(
            raw_output='{"keywords":[]}',
            provider=self.provider_name,
            used=False,
        )
