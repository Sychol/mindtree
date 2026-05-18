from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.reply import Reply
from app.repositories.base import BaseRepository


class ReplyRepository(BaseRepository[Reply]):
    def __init__(self, db: Session) -> None:
        super().__init__(db, Reply)

    def create_reply(
        self,
        *,
        event_id: UUID,
        session_id: UUID | None,
        target_card_id: UUID | None,
        reply_type: str,
        content_raw: str,
        content_redacted: str | None,
        safety_status: str,
        public_status: str,
        moderation_reason: str | None,
        origin: str | None = None,
        origin_tag: str | None = None,
        created_by_admin_id: UUID | None = None,
        reviewed_by: UUID | None = None,
        reviewed_at=None,
    ) -> Reply:
        reply = Reply(
            event_id=event_id,
            session_id=session_id,
            target_card_id=target_card_id,
            reply_type=reply_type,
            content_raw=content_raw,
            content_redacted=content_redacted,
            safety_status=safety_status,
            public_status=public_status,
            moderation_reason=moderation_reason,
            origin=origin or "participant",
            origin_tag=origin_tag,
            created_by_admin_id=created_by_admin_id,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
        )
        self.db.add(reply)
        self.db.flush()
        return reply

    def list_by_session_id(self, session_id: UUID) -> list[Reply]:
        statement = select(Reply).where(Reply.session_id == session_id)
        return list(self.db.execute(statement).scalars())

    def count_by_session_id(self, session_id: UUID) -> int:
        return len(self.list_by_session_id(session_id))

    def list_admin_replies(
        self,
        *,
        event_id: UUID,
        status_filter: str,
        origin_filter: str = "all",
        limit: int,
        offset: int,
    ) -> list[Reply]:
        statement = select(Reply).where(Reply.event_id == event_id)
        statement = _apply_reply_status_filter(statement, status_filter)
        statement = _apply_reply_origin_filter(statement, origin_filter)
        statement = statement.order_by(desc(Reply.created_at)).limit(limit).offset(offset)
        return list(self.db.execute(statement).scalars())

    def count_admin_replies(self, *, event_id: UUID, status_filter: str, origin_filter: str = "all") -> int:
        statement = select(func.count(Reply.id)).where(Reply.event_id == event_id)
        statement = _apply_reply_status_filter(statement, status_filter)
        statement = _apply_reply_origin_filter(statement, origin_filter)
        return int(self.db.execute(statement).scalar_one() or 0)


def _apply_reply_status_filter(statement, status_filter: str):
    if status_filter == "all":
        return statement
    if status_filter in {"safe", "review", "exclude"}:
        return statement.where(Reply.safety_status == status_filter)
    if status_filter in {"pending", "public", "hidden", "excluded"}:
        return statement.where(Reply.public_status == status_filter)
    return statement.where(Reply.safety_status == "review")


def _apply_reply_origin_filter(statement, origin_filter: str):
    if origin_filter == "all":
        return statement
    return statement.where(Reply.origin == origin_filter)
