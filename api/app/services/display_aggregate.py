from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import status
from sqlalchemy.orm import Session as SQLAlchemySession

from app.core.errors import AppError, ErrorCode
from app.repositories.display import DisplayKeywordRow, DisplayRepository
from app.schemas.display import DisplayKeyword, DisplaySnapshotResponse

TOP_KEYWORD_LIMIT = 5
CLOUD_KEYWORD_LIMIT = 40


@dataclass
class _KeywordBucket:
    text: str
    display_part: str
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
        bucket_key = f"{row.display_part}:{row.text}"
        bucket = buckets.setdefault(bucket_key, _KeywordBucket(text=row.text, display_part=row.display_part))
        bucket.add(row)
    return buckets


def _rank_keywords(
    buckets: dict[str, _KeywordBucket],
    *,
    categories: set[str] | None,
    display_parts: set[str] | None = None,
    limit: int,
    include_category: bool,
    include_display_part: bool = False,
) -> list[DisplayKeyword]:
    ranked: list[tuple[str, Decimal, str, str]] = []
    for bucket in buckets.values():
        if display_parts is not None and bucket.display_part not in display_parts:
            continue
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
        ranked.append((bucket.text, weight, bucket.primary_category, bucket.display_part))

    ranked.sort(key=lambda item: (-item[1], item[0]))
    return [
        DisplayKeyword(
            text=text,
            weight=_weight_to_float(weight),
            category=category if include_category else None,
            displayPart=display_part if include_display_part else None,
        )
        for text, weight, category, display_part in ranked[:limit]
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
            categories=None,
            display_parts={"trunk"},
            limit=TOP_KEYWORD_LIMIT,
            include_category=False,
        ),
        topSupportKeywords=_rank_keywords(
            buckets,
            categories=None,
            display_parts={"canopy"},
            limit=TOP_KEYWORD_LIMIT,
            include_category=False,
        ),
        cloudKeywords=_rank_keywords(
            buckets,
            categories=None,
            limit=CLOUD_KEYWORD_LIMIT,
            include_category=True,
            include_display_part=True,
        ),
        generatedAt=datetime.now(timezone.utc),
    )
