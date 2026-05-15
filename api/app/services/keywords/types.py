from __future__ import annotations

from dataclasses import dataclass

from app.models.enums import KeywordCategory, KeywordExtractionMethod

ALLOWED_KEYWORD_CATEGORIES = {category.value for category in KeywordCategory}
ALLOWED_EXTRACTION_METHODS = {method.value for method in KeywordExtractionMethod}


@dataclass(frozen=True)
class KeywordCandidate:
    text: str
    normalized: str
    category: str = KeywordCategory.NEUTRAL.value
    weight: float = 1.0
    extraction_method: str = KeywordExtractionMethod.FALLBACK.value

    def with_updates(
        self,
        *,
        text: str | None = None,
        normalized: str | None = None,
        category: str | None = None,
        weight: float | None = None,
        extraction_method: str | None = None,
    ) -> "KeywordCandidate":
        return KeywordCandidate(
            text=text if text is not None else self.text,
            normalized=normalized if normalized is not None else self.normalized,
            category=category if category is not None else self.category,
            weight=weight if weight is not None else self.weight,
            extraction_method=extraction_method if extraction_method is not None else self.extraction_method,
        )
