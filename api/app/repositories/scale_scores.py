from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.score import ScaleScore
from app.repositories.base import BaseRepository


class ScaleScoreRepository(BaseRepository[ScaleScore]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, ScaleScore)

    def list_by_session_id(self, session_id: UUID) -> list[ScaleScore]:
        statement = select(ScaleScore).where(ScaleScore.session_id == session_id)
        return list(self.db.execute(statement).scalars())

    def get_by_session_and_scale(
        self,
        session_id: UUID,
        scale_code: str,
    ) -> ScaleScore | None:
        statement = select(ScaleScore).where(
            ScaleScore.session_id == session_id,
            ScaleScore.scale_code == scale_code,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def upsert_scale_score(
        self,
        *,
        event_id: UUID,
        session_id: UUID,
        scale_code: str,
        raw_score: Decimal,
        severity_level: str | None,
        sub_scores: dict[str, Any],
        rule_version: str,
    ) -> ScaleScore:
        scale_score = self.get_by_session_and_scale(session_id, scale_code)
        if scale_score is None:
            scale_score = ScaleScore(
                event_id=event_id,
                session_id=session_id,
                scale_code=scale_code,
            )

        scale_score.raw_score = raw_score
        scale_score.severity_level = severity_level
        scale_score.sub_scores = sub_scores
        scale_score.rule_version = rule_version
        self.db.add(scale_score)
        self.db.flush()
        return scale_score
