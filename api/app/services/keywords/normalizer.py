from __future__ import annotations

import re
from collections.abc import Iterable

from app.models.enums import KeywordCategory, KeywordExtractionMethod
from app.services.keywords.synonym_map import apply_synonym
from app.services.keywords.types import (
    ALLOWED_EXTRACTION_METHODS,
    ALLOWED_KEYWORD_CATEGORIES,
    KeywordCandidate,
)
from app.services.safety_filter import (
    ABUSE_PATTERN,
    AFFILIATION_PATTERN,
    CRISIS_PATTERN,
    EMAIL_PATTERN,
    MEDICAL_ASSERTION_PATTERN,
    PHONE_PATTERN,
    SPECIFIC_EVENT_PATTERN,
    URL_PATTERN,
)

MAX_KEYWORDS = 5
MAX_KEYWORD_LENGTH = 12
ALLOWED_SINGLE_CHAR_KEYWORDS = {"잠", "쉼"}

STOPWORDS = {
    "나",
    "너",
    "우리",
    "오늘",
    "그냥",
    "정말",
    "많이",
    "조금",
    "때문에",
    "하지만",
    "그래도",
    "그리고",
    "하는",
    "했다",
    "있다",
    "없다",
    "입니다",
    "합니다",
    "해요",
    "돼요",
}

_TRIM_PATTERN = re.compile(r"^[^\w가-힣]+|[^\w가-힣]+$")
_SPACES_PATTERN = re.compile(r"\s+")
_SENSITIVE_PATTERNS = (
    PHONE_PATTERN,
    EMAIL_PATTERN,
    URL_PATTERN,
    AFFILIATION_PATTERN,
    SPECIFIC_EVENT_PATTERN,
    CRISIS_PATTERN,
    ABUSE_PATTERN,
    MEDICAL_ASSERTION_PATTERN,
)

_CATEGORY_BY_KEYWORD = {
    "긴장": KeywordCategory.MIND_SIGNAL.value,
    "답답함": KeywordCategory.MIND_SIGNAL.value,
    "피로": KeywordCategory.MIND_SIGNAL.value,
    "잠": KeywordCategory.MIND_SIGNAL.value,
    "쉼": KeywordCategory.RECOVERY.value,
    "회복": KeywordCategory.RECOVERY.value,
    "호흡": KeywordCategory.RECOVERY.value,
    "안정": KeywordCategory.RECOVERY.value,
    "괜찮아": KeywordCategory.SUPPORT.value,
    "응원": KeywordCategory.SUPPORT.value,
    "감사": KeywordCategory.SUPPORT.value,
    "위로": KeywordCategory.SUPPORT.value,
    "산책": KeywordCategory.COPING.value,
    "물마시기": KeywordCategory.COPING.value,
    "작은실천": KeywordCategory.COPING.value,
}


def compact_spaces(value: str) -> str:
    return _SPACES_PATTERN.sub(" ", value.strip())


def sanitize_text(value: str) -> str:
    sanitized = value
    for pattern in _SENSITIVE_PATTERNS:
        sanitized = pattern.sub(" ", sanitized)
    return compact_spaces(sanitized)


def contains_sensitive_pattern(value: str) -> bool:
    return any(pattern.search(value) for pattern in _SENSITIVE_PATTERNS)


def normalize_keyword_text(value: str) -> str:
    normalized = compact_spaces(value)
    normalized = _TRIM_PATTERN.sub("", normalized)
    normalized = normalized.strip(".,!?;:()[]{}<>\"'")
    return compact_spaces(normalized)


def infer_category(normalized: str, proposed_category: str | None = None) -> str:
    if normalized in _CATEGORY_BY_KEYWORD:
        return _CATEGORY_BY_KEYWORD[normalized]
    if proposed_category in ALLOWED_KEYWORD_CATEGORIES:
        return proposed_category
    return KeywordCategory.NEUTRAL.value


def _valid_weight(value: float) -> float:
    try:
        weight = float(value)
    except (TypeError, ValueError):
        return 1.0
    if weight <= 0:
        return 1.0
    return min(weight, 5.0)


def _is_allowed_keyword(value: str) -> bool:
    if not value:
        return False
    if value in STOPWORDS:
        return False
    if len(value) == 1 and value not in ALLOWED_SINGLE_CHAR_KEYWORDS:
        return False
    if len(value) > MAX_KEYWORD_LENGTH:
        return False
    if contains_sensitive_pattern(value):
        return False
    return True


def normalize_candidates(
    candidates: Iterable[KeywordCandidate],
    *,
    extraction_method: str | None = None,
    max_keywords: int = MAX_KEYWORDS,
) -> list[KeywordCandidate]:
    merged: dict[str, KeywordCandidate] = {}
    safe_limit = max(0, min(max_keywords, MAX_KEYWORDS))
    if safe_limit == 0:
        return []

    for candidate in candidates:
        method = extraction_method or candidate.extraction_method
        if method not in ALLOWED_EXTRACTION_METHODS:
            method = KeywordExtractionMethod.FALLBACK.value

        text = normalize_keyword_text(candidate.text)
        normalized = normalize_keyword_text(candidate.normalized or text)
        normalized = apply_synonym(normalized)
        text = apply_synonym(text) if text else normalized

        if not _is_allowed_keyword(text) or not _is_allowed_keyword(normalized):
            continue

        category = infer_category(normalized, candidate.category)
        normalized_candidate = KeywordCandidate(
            text=text,
            normalized=normalized,
            category=category,
            weight=_valid_weight(candidate.weight),
            extraction_method=method,
        )
        existing = merged.get(normalized)
        if existing is None or normalized_candidate.weight > existing.weight:
            merged[normalized] = normalized_candidate

    return list(merged.values())[:safe_limit]
