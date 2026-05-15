import os
from collections.abc import Callable, Generator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

os.environ.setdefault(
    "DATABASE_URL",
    os.getenv("TEST_DATABASE_URL")
    or "postgresql+psycopg://maeumnamu:maeumnamu_dev_password@localhost:5432/maeumnamu",
)

os.environ.setdefault(
    "JWT_SECRET_KEY",
    os.getenv("TEST_JWT_SECRET_KEY")
    or os.getenv("JWT_SECRET_KEY")
    or "change-me-in-local-only",
)

from app import models  # noqa: E402,F401
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db, get_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.consent import ConsentLog  # noqa: E402
from app.models.answer import Answer  # noqa: E402
from app.models.card import CardSelection, MindCard  # noqa: E402
from app.models.completion import CompletionCode  # noqa: E402
from app.models.audit import AdminAuditLog  # noqa: E402
from app.models.event import Event  # noqa: E402
from app.models.keyword import Keyword, KeywordJob  # noqa: E402
from app.models.question import Question  # noqa: E402
from app.models.reply import Reply  # noqa: E402
from app.models.risk import RiskFlag  # noqa: E402
from app.models.score import ScaleScore  # noqa: E402
from app.models.session import Session as EventSession  # noqa: E402
from app.models.summary import Summary  # noqa: E402

get_settings.cache_clear()
get_engine.cache_clear()

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest.fixture(scope="session", autouse=True)
def prepare_database() -> None:
    Base.metadata.create_all(bind=get_engine())


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal(bind=get_engine())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal(bind=get_engine())
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def event_factory(db_session: Session) -> Generator[Callable[..., Event], None, None]:
    event_ids = []

    def create_event(
        *,
        status: str = "open",
        slug: str | None = None,
        consent_version: str = "v1",
        settings: dict | None = None,
    ) -> Event:
        event = Event(
            slug=slug or f"phase03-fire-expo-2026-{uuid4().hex}",
            name="마음나무",
            description="소방안전박람회 마음점검 이벤트",
            status=status,
            consent_version=consent_version,
            settings=settings
            or {
                "displayEnabled": True,
                "maxMindCardsPerSession": 3,
                "helpNoticeEnabled": True,
                "llmEnabled": False,
            },
        )
        db_session.add(event)
        db_session.commit()
        db_session.refresh(event)
        event_ids.append(event.id)
        return event

    yield create_event

    for event_id in reversed(event_ids):
        db_session.execute(delete(AdminAuditLog).where(AdminAuditLog.event_id == event_id))
        db_session.execute(delete(CompletionCode).where(CompletionCode.event_id == event_id))
        db_session.execute(delete(Reply).where(Reply.event_id == event_id))
        db_session.execute(delete(CardSelection).where(CardSelection.event_id == event_id))
        db_session.execute(delete(Keyword).where(Keyword.event_id == event_id))
        db_session.execute(delete(KeywordJob).where(KeywordJob.event_id == event_id))
        db_session.execute(delete(MindCard).where(MindCard.event_id == event_id))
        db_session.execute(delete(Summary).where(Summary.event_id == event_id))
        db_session.execute(delete(RiskFlag).where(RiskFlag.event_id == event_id))
        db_session.execute(delete(ScaleScore).where(ScaleScore.event_id == event_id))
        db_session.execute(delete(Answer).where(Answer.event_id == event_id))
        db_session.execute(delete(Question).where(Question.event_id == event_id))
        db_session.execute(delete(ConsentLog).where(ConsentLog.event_id == event_id))
        db_session.execute(delete(EventSession).where(EventSession.event_id == event_id))
        db_session.execute(delete(Event).where(Event.id == event_id))
    db_session.commit()
