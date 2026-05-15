from collections.abc import Iterable
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.keyword import Keyword
from app.repositories.base import BaseRepository
from app.services.keywords.types import KeywordCandidate


class KeywordRepository(BaseRepository[Keyword]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Keyword)

    def delete_keywords_by_job_id(self, job_id: UUID) -> None:
        self.db.execute(delete(Keyword).where(Keyword.job_id == job_id))
        self.db.flush()

    def create_keywords(
        self,
        *,
        event_id: UUID,
        source_type: str,
        source_id: UUID,
        job_id: UUID,
        candidates: Iterable[KeywordCandidate],
        status: str = "active",
    ) -> list[Keyword]:
        merged: dict[str, KeywordCandidate] = {}
        for candidate in candidates:
            existing = merged.get(candidate.normalized)
            if existing is None or candidate.weight > existing.weight:
                merged[candidate.normalized] = candidate

        keywords: list[Keyword] = []
        for candidate in merged.values():
            keyword = Keyword(
                event_id=event_id,
                source_type=source_type,
                source_id=source_id,
                keyword_text=candidate.text,
                normalized_keyword=candidate.normalized,
                category=candidate.category,
                weight=Decimal(str(candidate.weight)),
                status=status,
                extraction_method=candidate.extraction_method,
                job_id=job_id,
            )
            self.db.add(keyword)
            keywords.append(keyword)

        self.db.flush()
        return keywords

    def list_keywords_by_source(
        self,
        *,
        source_type: str,
        source_id: UUID,
    ) -> list[Keyword]:
        statement = (
            select(Keyword)
            .where(
                Keyword.source_type == source_type,
                Keyword.source_id == source_id,
            )
            .order_by(Keyword.created_at.asc())
        )
        return list(self.db.execute(statement).scalars())

    def list_admin_keywords(
        self,
        *,
        event_id: UUID,
        status_filter: str,
        category: str | None,
        limit: int,
        offset: int,
    ) -> list[Keyword]:
        statement = select(Keyword).where(Keyword.event_id == event_id)
        if status_filter != "all":
            statement = statement.where(Keyword.status == status_filter)
        if category:
            statement = statement.where(Keyword.category == category)
        statement = statement.order_by(Keyword.created_at.desc()).limit(limit).offset(offset)
        return list(self.db.execute(statement).scalars())

    def count_admin_keywords(
        self,
        *,
        event_id: UUID,
        status_filter: str,
        category: str | None,
    ) -> int:
        statement = select(func.count(Keyword.id)).where(Keyword.event_id == event_id)
        if status_filter != "all":
            statement = statement.where(Keyword.status == status_filter)
        if category:
            statement = statement.where(Keyword.category == category)
        return int(self.db.execute(statement).scalar_one() or 0)

    def update_status_by_source(
        self,
        *,
        event_id: UUID,
        source_type: str,
        source_id: UUID,
        status: str,
    ) -> int:
        keywords = self.list_keywords_by_source(source_type=source_type, source_id=source_id)
        for keyword in keywords:
            if keyword.event_id != event_id:
                continue
            keyword.status = status
            self.db.add(keyword)
        self.db.flush()
        return len(keywords)
