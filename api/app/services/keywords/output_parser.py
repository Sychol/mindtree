from __future__ import annotations

import json
from typing import Any

from app.models.enums import KeywordCategory, KeywordExtractionMethod
from app.services.keywords.normalizer import normalize_candidates
from app.services.keywords.types import ALLOWED_KEYWORD_CATEGORIES, KeywordCandidate


class KeywordOutputParseError(ValueError):
    pass


def _parse_weight(value: Any) -> float:
    try:
        weight = float(value)
    except (TypeError, ValueError) as exc:
        raise KeywordOutputParseError("keyword weight must be numeric") from exc
    if weight <= 0:
        raise KeywordOutputParseError("keyword weight must be positive")
    return min(weight, 5.0)


def parse_keyword_output(raw_output: str, *, extraction_method: str = KeywordExtractionMethod.LLM.value) -> list[KeywordCandidate]:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise KeywordOutputParseError("LLM keyword output is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise KeywordOutputParseError("LLM keyword output must be an object")

    raw_keywords = payload.get("keywords", [])
    if raw_keywords is None:
        return []
    if not isinstance(raw_keywords, list):
        raise KeywordOutputParseError("keywords must be an array")

    candidates: list[KeywordCandidate] = []
    for item in raw_keywords[:5]:
        if not isinstance(item, dict):
            raise KeywordOutputParseError("keyword item must be an object")

        text = item.get("text")
        normalized = item.get("normalized") or text
        if not isinstance(text, str) or not text.strip():
            raise KeywordOutputParseError("keyword text is required")
        if not isinstance(normalized, str) or not normalized.strip():
            raise KeywordOutputParseError("keyword normalized value is required")

        category = item.get("category", KeywordCategory.NEUTRAL.value)
        if category not in ALLOWED_KEYWORD_CATEGORIES:
            category = KeywordCategory.NEUTRAL.value

        candidates.append(
            KeywordCandidate(
                text=text,
                normalized=normalized,
                category=category,
                weight=_parse_weight(item.get("weight", 1.0)),
                extraction_method=extraction_method,
            )
        )

    return normalize_candidates(
        candidates,
        extraction_method=extraction_method,
        max_keywords=5,
    )
