from __future__ import annotations

import re

from app.models.enums import KeywordCategory, KeywordExtractionMethod
from app.services.keywords.normalizer import STOPWORDS, normalize_candidates, sanitize_text
from app.services.keywords.types import KeywordCandidate

_KOREAN_TOKEN_PATTERN = re.compile(r"[가-힣A-Za-z0-9]+")

_PATTERN_CANDIDATES: tuple[tuple[re.Pattern[str], tuple[tuple[str, str], ...]], ...] = (
    (
        re.compile(r"(잠|불면|못\s*자|안\s*와)"),
        (
            ("잠", KeywordCategory.MIND_SIGNAL.value),
            ("피로", KeywordCategory.MIND_SIGNAL.value),
        ),
    ),
    (
        re.compile(r"(가슴.*답답|답답|숨막|막막)"),
        (
            ("답답함", KeywordCategory.MIND_SIGNAL.value),
            ("긴장", KeywordCategory.MIND_SIGNAL.value),
        ),
    ),
    (
        re.compile(r"(괜찮|쉬어|쉬다|휴식)"),
        (
            ("괜찮아", KeywordCategory.SUPPORT.value),
            ("쉼", KeywordCategory.RECOVERY.value),
        ),
    ),
    (
        re.compile(r"(버텼|버텨|견뎠|견뎌)"),
        (
            ("버팀", KeywordCategory.MIND_SIGNAL.value),
            ("회복", KeywordCategory.RECOVERY.value),
        ),
    ),
    (
        re.compile(r"(숨|호흡|천천히)"),
        (
            ("호흡", KeywordCategory.RECOVERY.value),
            ("안정", KeywordCategory.RECOVERY.value),
        ),
    ),
    (
        re.compile(r"(고마|감사)"),
        (
            ("감사", KeywordCategory.SUPPORT.value),
            ("응원", KeywordCategory.SUPPORT.value),
        ),
    ),
    (
        re.compile(r"(불안|초조|긴장|떨림)"),
        (("긴장", KeywordCategory.MIND_SIGNAL.value),),
    ),
    (
        re.compile(r"(피곤|지침|지쳐|소진|번아웃)"),
        (("피로", KeywordCategory.MIND_SIGNAL.value),),
    ),
    (
        re.compile(r"(산책|걷기|걸어)"),
        (("산책", KeywordCategory.COPING.value),),
    ),
    (
        re.compile(r"(물\s*한\s*잔|물마시|물\s*마시)"),
        (("물마시기", KeywordCategory.COPING.value),),
    ),
    (
        re.compile(r"(위로|토닥|혼자\s*아니)"),
        (("위로", KeywordCategory.SUPPORT.value),),
    ),
)

_TOKEN_CATEGORY = {
    "쉼": KeywordCategory.RECOVERY.value,
    "회복": KeywordCategory.RECOVERY.value,
    "호흡": KeywordCategory.RECOVERY.value,
    "안정": KeywordCategory.RECOVERY.value,
    "긴장": KeywordCategory.MIND_SIGNAL.value,
    "피로": KeywordCategory.MIND_SIGNAL.value,
    "응원": KeywordCategory.SUPPORT.value,
    "감사": KeywordCategory.SUPPORT.value,
    "위로": KeywordCategory.SUPPORT.value,
}


def _candidate(text: str, category: str, weight: float = 1.0) -> KeywordCandidate:
    return KeywordCandidate(
        text=text,
        normalized=text,
        category=category,
        weight=weight,
        extraction_method=KeywordExtractionMethod.FALLBACK.value,
    )


def _token_candidates(text: str) -> list[KeywordCandidate]:
    candidates: list[KeywordCandidate] = []
    for token in _KOREAN_TOKEN_PATTERN.findall(text):
        cleaned = token.strip()
        if cleaned in STOPWORDS or len(cleaned) <= 1:
            continue
        category = _TOKEN_CATEGORY.get(cleaned)
        if category is None:
            continue
        candidates.append(_candidate(cleaned, category, 0.8))
    return candidates


def extract_fallback_keywords(
    text: str,
    *,
    source_type: str,
    source_hint: str | None = None,
    max_keywords: int = 5,
) -> list[KeywordCandidate]:
    del source_type, source_hint
    sanitized = sanitize_text(text)
    if not sanitized:
        return []

    candidates: list[KeywordCandidate] = []
    for pattern, keyword_specs in _PATTERN_CANDIDATES:
        if pattern.search(sanitized):
            for keyword_text, category in keyword_specs:
                candidates.append(_candidate(keyword_text, category))

    candidates.extend(_token_candidates(sanitized))
    return normalize_candidates(
        candidates,
        extraction_method=KeywordExtractionMethod.FALLBACK.value,
        max_keywords=max_keywords,
    )
