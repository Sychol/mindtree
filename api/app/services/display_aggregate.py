from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.models.enums import KeywordCategory
from app.repositories.display import DisplayKeywordRow, DisplayRepository
from app.schemas.display import DisplayKeyword, DisplaySnapshotResponse

TOP_KEYWORD_LIMIT = 5
CLOUD_KEYWORD_LIMIT = 40
SUPPORT_CATEGORIES = {
    KeywordCategory.SUPPORT.value,
    KeywordCategory.RECOVERY.value,
    KeywordCategory.COPING.value,
}


@dataclass
class _KeywordBucket:
    text: str
    total_weight: Decimal = Decimal("0")
    category_weights: dict[str, Decimal] = field(default_factory=lambda: defaultdict(lambda: Decimal("0")))

    def add(self, row: DisplayKeywordRow) -> None:
        self.total_weight += row.weight
        self.category_weights[row.category] += row.weight

    @property
    def primary_category(self) -> str:
        return sorted(
            self.category_weights.items(),
            key=lambda item: (-item[1], item[0]),
        )[0][0]


def _weight_to_float(value: Decimal) -> float:
    return float(value)


def _aggregate_rows(rows: list[DisplayKeywordRow]) -> dict[str, _KeywordBucket]:
    buckets: dict[str, _KeywordBucket] = {}
    for row in rows:
        if not row.text:
            continue
        bucket = buckets.setdefault(row.text, _KeywordBucket(text=row.text))
        bucket.add(row)
    return buckets


def _rank_keywords(
    buckets: dict[str, _KeywordBucket],
    *,
    categories: set[str] | None,
    limit: int,
    include_category: bool,
) -> list[DisplayKeyword]:
    ranked: list[tuple[str, Decimal, str]] = []
    for text, bucket in buckets.items():
        if categories is None:
            weight = bucket.total_weight
        else:
            weight = sum(
                category_weight
                for category, category_weight in bucket.category_weights.items()
                if category in categories
            )
        if weight <= 0:
            continue
        ranked.append((text, weight, bucket.primary_category))

    ranked.sort(key=lambda item: (-item[1], item[0]))
    return [
        DisplayKeyword(
            text=text,
            weight=_weight_to_float(weight),
            category=category if include_category else None,
        )
        for text, weight, category in ranked[:limit]
    ]


def build_display_snapshot(
    db: SQLAlchemySession,
    event_slug: str,
) -> DisplaySnapshotResponse:
    repository = DisplayRepository(db)
    event = repository.get_event_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    rows = repository.list_display_keyword_rows(event.id)
    buckets = _aggregate_rows(rows)

    # participantCount intentionally counts all sessions created for the event.
    # completedCount follows the field policy: a completion code means the flow
    # reached the real-world completion point.
    return DisplaySnapshotResponse(
        eventSlug=event.slug,
        participantCount=repository.count_event_sessions(event.id),
        completedCount=repository.count_completed_sessions(event.id),
        topMindKeywords=_rank_keywords(
            buckets,
            categories={KeywordCategory.MIND_SIGNAL.value},
            limit=TOP_KEYWORD_LIMIT,
            include_category=False,
        ),
        topSupportKeywords=_rank_keywords(
            buckets,
            categories=SUPPORT_CATEGORIES,
            limit=TOP_KEYWORD_LIMIT,
            include_category=False,
        ),
        cloudKeywords=_rank_keywords(
            buckets,
            categories=None,
            limit=CLOUD_KEYWORD_LIMIT,
            include_category=True,
        ),
        generatedAt=datetime.now(timezone.utc),
    )
