from fastapi import status
from sqlalchemy.orm import Session

from app.core.errors import AppError, ErrorCode
from app.models.enums import EventStatus
from app.repositories.events import EventRepository
from app.schemas.events import (
    PublicEvent,
    PublicEventNotices,
    PublicEventResponse,
    PublicEventSettings,
)

NOTICES = PublicEventNotices(
    not_diagnosis="본 이벤트는 진단이나 치료가 아닌 체험형 마음 점검입니다.",
    anonymous_keyword_display="TV에는 원문이 아닌 익명 키워드만 표시됩니다.",
)


def _public_settings(settings: dict) -> PublicEventSettings:
    return PublicEventSettings(
        display_enabled=bool(settings.get("displayEnabled", False)),
        max_mind_cards_per_session=int(settings.get("maxMindCardsPerSession", 3)),
        help_notice_enabled=bool(settings.get("helpNoticeEnabled", True)),
    )


def get_public_event(db: Session, event_slug: str) -> PublicEventResponse:
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise AppError(
            ErrorCode.EVENT_NOT_FOUND,
            "이벤트를 찾을 수 없습니다.",
            status.HTTP_404_NOT_FOUND,
        )

    if event.status != EventStatus.OPEN.value:
        raise AppError(
            ErrorCode.EVENT_NOT_OPEN,
            "공개 진입 가능한 이벤트가 아닙니다.",
            status.HTTP_403_FORBIDDEN,
            details={"status": event.status},
        )

    return PublicEventResponse(
        event=PublicEvent(
            slug=event.slug,
            name=event.name,
            status=event.status,
            description=event.description,
            consent_version=event.consent_version,
            settings=_public_settings(event.settings or {}),
        ),
        notices=NOTICES,
    )
