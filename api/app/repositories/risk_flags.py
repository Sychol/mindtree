from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.risk import RiskFlag
from app.repositories.base import BaseRepository


class RiskFlagRepository(BaseRepository[RiskFlag]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, RiskFlag)

    def get_by_session_id(self, session_id: UUID) -> RiskFlag | None:
        statement = select(RiskFlag).where(RiskFlag.session_id == session_id)
        return self.db.execute(statement).scalar_one_or_none()

    def upsert_risk_flags(
        self,
        *,
        event_id: UUID,
        session_id: UUID,
        phq9_item9_positive: bool,
        crisis_expression_detected: bool,
        trauma_high_signal: bool,
        moral_injury_high_signal: bool,
        public_restriction: bool,
        help_notice_required: bool,
        details: dict[str, Any],
        rule_version: str,
    ) -> RiskFlag:
        risk_flag = self.get_by_session_id(session_id)
        if risk_flag is None:
            risk_flag = RiskFlag(event_id=event_id, session_id=session_id)

        risk_flag.phq9_item9_positive = phq9_item9_positive
        risk_flag.crisis_expression_detected = crisis_expression_detected
        risk_flag.trauma_high_signal = trauma_high_signal
        risk_flag.moral_injury_high_signal = moral_injury_high_signal
        risk_flag.public_restriction = public_restriction
        risk_flag.help_notice_required = help_notice_required
        risk_flag.details = details
        risk_flag.rule_version = rule_version
        self.db.add(risk_flag)
        self.db.flush()
        return risk_flag

    def mark_crisis_expression_detected(
        self,
        *,
        event_id: UUID,
        session_id: UUID,
        reason: str,
    ) -> RiskFlag:
        risk_flag = self.get_by_session_id(session_id)
        if risk_flag is None:
            risk_flag = RiskFlag(event_id=event_id, session_id=session_id)

        details = dict(risk_flag.details or {})
        safety_filter_details = dict(details.get("safety_filter") or {})
        safety_filter_details["crisis_expression_detected"] = True
        safety_filter_details["reason"] = reason
        details["safety_filter"] = safety_filter_details

        risk_flag.crisis_expression_detected = True
        risk_flag.public_restriction = True
        risk_flag.help_notice_required = True
        risk_flag.details = details
        self.db.add(risk_flag)
        self.db.flush()
        return risk_flag
