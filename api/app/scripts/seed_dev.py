from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.passwords import hash_password
from app.db.session import get_engine
from app.models.admin import AdminUser
from app.models.card import MindCard
from app.models.enums import PublicStatus, SafetyStatus, SessionStatus
from app.models.event import Event
from app.models.keyword import KeywordJob
from app.models.risk import RiskFlag
from app.models.session import Session as EventSession
from app.repositories.admin_users import AdminUserRepository
from app.repositories.keyword_jobs import KeywordJobRepository
from app.scripts.seed_questions import seed_questions_for_event
from app.services.keyword_job_factory import create_keyword_job_for_card

EVENT_SLUG = "fire-expo-2026"
EVENT_NAME = "Maeumnamu Field Rehearsal"
SEED_CARD_CONTENTS = [
    "\uad1c\ucc2e\uc544\uc694 \uc26c\uc5b4\uac00\ub3c4 \ub3fc\uc694",
    "\uc228\uc744 \ucc9c\ucc9c\ud788 \uc26c\uc5b4\ubd10\uc694",
    "\uc624\ub298\ub3c4 \ubc84\ud168\uc5b4\uc694",
]


@dataclass(frozen=True)
class SeedDevResult:
    event_created: bool
    questions_created: int
    questions_updated: int
    questions_deleted_stale: int
    admin_created: bool
    admin_skipped: bool
    cards_created: int
    keyword_jobs_created: int


def _event_settings() -> dict[str, object]:
    return {
        "displayEnabled": True,
        "maxMindCardsPerSession": 3,
        "helpNoticeEnabled": True,
        "completionCodePrefix": "TREE",
        "llmEnabled": False,
    }


def _ensure_event(db: Session) -> tuple[Event, bool]:
    event = db.execute(select(Event).where(Event.slug == EVENT_SLUG)).scalar_one_or_none()
    if event is None:
        event = Event(
            slug=EVENT_SLUG,
            name=EVENT_NAME,
            description="Local field rehearsal event for Maeumnamu.",
            status="open",
            consent_version="v1",
            settings=_event_settings(),
        )
        db.add(event)
        db.flush()
        return event, True

    event.status = "open"
    event.consent_version = "v1"
    event.settings = {**_event_settings(), **(event.settings or {})}
    db.add(event)
    db.flush()
    return event, False


def _ensure_admin(db: Session) -> tuple[bool, bool]:
    settings = get_settings()
    email = settings.admin_bootstrap_email.strip().lower()
    password = settings.admin_bootstrap_password
    display_name = settings.admin_bootstrap_display_name.strip() or "Operator"
    if not email or not password:
        return False, True

    repo = AdminUserRepository(db)
    existing = repo.get_by_email(email)
    if existing is not None:
        return False, False

    repo.create_admin_user(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        role="operator",
        is_active=True,
    )
    return True, False


def _seed_session_key(index: int) -> str:
    return f"seed-dev-public-card-{index}"


def _ensure_seed_session(db: Session, event: Event, index: int) -> EventSession:
    key = _seed_session_key(index)
    session = db.execute(
        select(EventSession).where(
            EventSession.event_id == event.id,
            EventSession.anonymous_key_hash == key,
        )
    ).scalar_one_or_none()
    if session is not None:
        session.status = SessionStatus.COMPLETED.value
        session.last_step = "complete"
        db.add(session)
        db.flush()
        return session

    session = EventSession(
        event_id=event.id,
        anonymous_key_hash=key,
        resume_token_hash=f"{key}-resume",
        status=SessionStatus.COMPLETED.value,
        last_step="complete",
        client_meta={"seed": "phase11"},
    )
    db.add(session)
    db.flush()
    return session


def _ensure_risk_flag(db: Session, event: Event, session: EventSession) -> None:
    risk = db.execute(
        select(RiskFlag).where(RiskFlag.session_id == session.id)
    ).scalar_one_or_none()
    if risk is None:
        risk = RiskFlag(
            event_id=event.id,
            session_id=session.id,
            details={"seed": "phase11"},
            rule_version="seed-dev",
        )
        db.add(risk)
        db.flush()


def _ensure_seed_cards(db: Session, event: Event) -> tuple[int, int]:
    cards_created = 0
    jobs_created = 0
    job_repo = KeywordJobRepository(db)

    for index, content in enumerate(SEED_CARD_CONTENTS, start=1):
        session = _ensure_seed_session(db, event, index)
        _ensure_risk_flag(db, event, session)
        card = db.execute(
            select(MindCard).where(
                MindCard.event_id == event.id,
                MindCard.content_raw == content,
            )
        ).scalar_one_or_none()
        if card is None:
            card = MindCard(
                event_id=event.id,
                session_id=session.id,
                prompt_type="to_colleague",
                content_raw=content,
                safety_status=SafetyStatus.SAFE.value,
                public_status=PublicStatus.PUBLIC.value,
            )
            db.add(card)
            db.flush()
            cards_created += 1
        else:
            card.safety_status = SafetyStatus.SAFE.value
            card.public_status = PublicStatus.PUBLIC.value
            db.add(card)
            db.flush()

        has_job = db.execute(
            select(KeywordJob).where(
                KeywordJob.source_type == "mind_card",
                KeywordJob.source_id == card.id,
            )
        ).first()
        if has_job is None and not job_repo.list_by_source("mind_card", card.id):
            create_keyword_job_for_card(db, card)
            jobs_created += 1

    return cards_created, jobs_created


def seed_dev(db: Session) -> SeedDevResult:
    event, event_created = _ensure_event(db)
    db.commit()

    question_result = seed_questions_for_event(db, event.slug)

    admin_created, admin_skipped = _ensure_admin(db)
    cards_created, jobs_created = _ensure_seed_cards(db, event)
    db.commit()

    return SeedDevResult(
        event_created=event_created,
        questions_created=question_result["created"],
        questions_updated=question_result["updated"],
        questions_deleted_stale=question_result["deletedStale"],
        admin_created=admin_created,
        admin_skipped=admin_skipped,
        cards_created=cards_created,
        keyword_jobs_created=jobs_created,
    )


def main() -> None:
    with Session(bind=get_engine()) as db:
        result = seed_dev(db)

    print(
        "seed_dev_complete "
        f"event_created={result.event_created} "
        f"questions_created={result.questions_created} "
        f"questions_updated={result.questions_updated} "
        f"questions_deleted_stale={result.questions_deleted_stale} "
        f"admin_created={result.admin_created} "
        f"admin_skipped={result.admin_skipped} "
        f"cards_created={result.cards_created} "
        f"keyword_jobs_created={result.keyword_jobs_created}"
    )


if __name__ == "__main__":
    main()
