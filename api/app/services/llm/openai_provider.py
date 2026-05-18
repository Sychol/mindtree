from __future__ import annotations

from typing import Any

from app.services.llm.base import LlmKeywordRequest, LlmKeywordResult

DEFAULT_KEYWORD_MODEL = "gpt-4.1-nano"
ALLOWED_CATEGORIES = ("mind_signal", "support", "recovery", "coping", "neutral")

KEYWORD_RESPONSE_FORMAT: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "mindtree_keyword_output",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "keywords": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "text": {"type": "string"},
                            "normalized": {"type": "string"},
                            "category": {"type": "string", "enum": list(ALLOWED_CATEGORIES)},
                            "weight": {"type": "number"},
                        },
                        "required": ["text", "normalized", "category", "weight"],
                    },
                },
            },
            "required": ["keywords"],
        },
    },
}

SYSTEM_INSTRUCTION = """너는 마음나무 이벤트의 키워드 추출 보조기다.
진단하지 않는다.
위험도나 자살위험을 판단하지 않는다.
공개 여부를 판단하지 않는다.
관리자 승인 여부를 판단하지 않는다.
원문을 요약하거나 재작성하지 않는다.
짧은 한국어 키워드만 추출한다.
개인정보, 실명, 구체 장소, 날짜, 사건명, 피해자 정보, 연락처는 키워드로 반환하지 않는다.
자해·자살·죽음 관련 직접 표현은 키워드로 반환하지 않는다.
반드시 지정된 JSON schema만 반환한다."""

MIND_CARD_INSTRUCTION = """입력은 참가자가 작성한 스트레스 상황 카드 또는 마음카드다.
마음에 남은 상태, 긴장, 피로, 죄책감, 답답함, 부담감, 회복 필요성 같은 마음신호 키워드를 우선 추출한다.
진단명이나 질병명은 사용하지 않는다.
가능한 category:
- mind_signal
- recovery
- coping
- neutral
support는 꼭 필요한 경우에만 사용한다."""

REPLY_INSTRUCTION = """입력은 타인의 마음카드에 남긴 응원·공감·작은 대처법 문장이다.
응원, 위로, 공감, 쉼, 회복, 호흡, 산책, 물마시기 같은 support/recovery/coping 키워드를 우선 추출한다.
가능한 category:
- support
- recovery
- coping
- neutral
mind_signal은 꼭 필요한 경우에만 사용한다."""

OUTPUT_INSTRUCTION = """반환 형식:
{
  "keywords": [
    {
      "text": "쉼",
      "normalized": "쉼",
      "category": "recovery",
      "weight": 1.0
    }
  ]
}

제약:
- keywords length: 0~5
- text: 1~12자
- normalized: 1~12자
- category: mind_signal | support | recovery | coping | neutral
- weight: 0.1~1.0
- JSON 외의 설명 문장은 반환하지 않는다."""

_TIMEOUT_ERROR_CLASS_NAMES = {
    "APITimeoutError",
    "ConnectTimeout",
    "ReadTimeout",
    "Timeout",
    "TimeoutError",
}


def _make_openai_client(*, api_key: str, timeout_seconds: int) -> Any:
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError("OpenAI SDK is not installed") from exc

    return OpenAI(api_key=api_key, timeout=timeout_seconds)


def _is_timeout_error(exc: Exception) -> bool:
    return exc.__class__.__name__ in _TIMEOUT_ERROR_CLASS_NAMES


def _source_instruction(source_type: str) -> str:
    if source_type == "reply":
        return REPLY_INSTRUCTION
    return MIND_CARD_INSTRUCTION


def build_keyword_messages(request: LlmKeywordRequest) -> list[dict[str, str]]:
    source_hint = request.source_hint or ""
    user_content = "\n\n".join(
        [
            _source_instruction(request.source_type),
            OUTPUT_INSTRUCTION,
            f"source_type: {request.source_type}",
            f"source_hint: {source_hint}",
            "input_text:\n" + request.text,
        ]
    )
    return [
        {"role": "system", "content": SYSTEM_INSTRUCTION},
        {"role": "user", "content": user_content},
    ]


def _extract_message_content(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if choices:
        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content

    if isinstance(response, dict):
        choices = response.get("choices")
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                return content

    return ""


class OpenAIKeywordLlmProvider:
    provider_name = "openai"

    def __init__(self, *, api_key: str, model: str, timeout_seconds: int) -> None:
        self.api_key = api_key.strip()
        self.model = model.strip() or DEFAULT_KEYWORD_MODEL
        self.timeout_seconds = max(int(timeout_seconds or 1), 1)
        self._client: Any | None = None

    @property
    def _openai_client(self) -> Any:
        if self._client is None:
            self._client = _make_openai_client(
                api_key=self.api_key,
                timeout_seconds=self.timeout_seconds,
            )
        return self._client

    def extract_keywords(self, request: LlmKeywordRequest) -> LlmKeywordResult:
        if not self.api_key:
            return LlmKeywordResult(raw_output='{"keywords":[]}', provider="disabled", used=False)

        try:
            response = self._openai_client.chat.completions.create(
                model=self.model,
                messages=build_keyword_messages(request),
                response_format=KEYWORD_RESPONSE_FORMAT,
                temperature=0,
                max_tokens=400,
            )
        except Exception as exc:
            if _is_timeout_error(exc):
                raise TimeoutError("LLM timeout") from exc
            raise

        raw_output = _extract_message_content(response).strip()
        if not raw_output:
            raise RuntimeError("OpenAI returned an empty keyword response")

        return LlmKeywordResult(
            raw_output=raw_output,
            provider=f"openai:{self.model}",
            used=True,
        )
