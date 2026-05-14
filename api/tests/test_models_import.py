from app.db.base import Base
from app.models import Event, Question, Session
from app.models.enums import CompletionCodeStatus, EventStatus, KeywordJobStatus, SessionStatus


def test_models_importable() -> None:
    assert Event is not None
    assert Session is not None
    assert Question is not None
    assert Base.metadata is not None


def test_documented_enum_values() -> None:
    assert EventStatus.OPEN == "open"
    assert SessionStatus.CREATED == "created"
    assert KeywordJobStatus.PENDING == "pending"
    assert CompletionCodeStatus.REDEEMED == "redeemed"
