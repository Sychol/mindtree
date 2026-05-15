from app.models.enums import KeywordCategory, KeywordExtractionMethod
from app.services.keywords.normalizer import normalize_candidates
from app.services.keywords.types import KeywordCandidate


def _candidate(text: str, normalized: str | None = None, category: str = "neutral") -> KeywordCandidate:
    return KeywordCandidate(
        text=text,
        normalized=normalized or text,
        category=category,
        weight=1.0,
        extraction_method=KeywordExtractionMethod.FALLBACK.value,
    )


def test_normalizer_trims_spaces_and_applies_synonym_map() -> None:
    result = normalize_candidates([_candidate("  휴식  ", "휴식")])

    assert len(result) == 1
    assert result[0].text == "쉼"
    assert result[0].normalized == "쉼"
    assert result[0].category == KeywordCategory.RECOVERY.value


def test_normalizer_filters_short_long_and_sensitive_keywords() -> None:
    result = normalize_candidates(
        [
            _candidate("나"),
            _candidate("x"),
            _candidate("너무길고구체적인키워드입니다"),
            _candidate("010-1234-5678"),
            _candidate("hello@example.com"),
            _candidate("https://example.com"),
            _candidate("자살"),
            _candidate("쉼"),
        ]
    )

    assert [candidate.normalized for candidate in result] == ["쉼"]


def test_normalizer_defaults_unknown_category_and_limits_to_five() -> None:
    result = normalize_candidates(
        [
            _candidate("긴장", category="bad"),
            _candidate("감사", category="bad"),
            _candidate("회복", category="bad"),
            _candidate("호흡", category="bad"),
            _candidate("산책", category="bad"),
            _candidate("응원", category="bad"),
        ]
    )

    assert len(result) == 5
    assert result[0].category == KeywordCategory.MIND_SIGNAL.value
