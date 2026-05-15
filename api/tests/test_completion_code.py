import re

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import CardSelection
from app.models.completion import CompletionCode
from app.models.enums import CompletionCodeStatus, SessionStatus
from app.models.session import Session as EventSession
from tests.test_cards_api import _card, _session


def _complete_session(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> tuple[EventSession, str]:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    _card(db_session, event, session, content="내 카드")
    peer_card = _card(db_session, event, peer_session)
    selection = CardSelection(
        event_id=event.id,
        session_id=session.id,
        selected_card_id=peer_card.id,
    )
    db_session.add(selection)
    db_session.commit()

    response = client.post(
        f"/api/sessions/{session.id}/replies",
        json={
            "targetCardId": str(peer_card.id),
            "replyType": "comfort",
            "content": "그 시간을 버틴 것만으로도 충분합니다.",
        },
    )
    assert response.status_code == 200
    return session, response.json()["completion"]["code"]


def test_completion_code_format_status_and_completed_at(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    session, code = _complete_session(client, db_session, event_factory)

    assert re.fullmatch(r"TREE-[A-Z2-9]{6}", code)

    db_session.expire_all()
    completion_code = db_session.execute(
        select(CompletionCode).where(CompletionCode.session_id == session.id)
    ).scalar_one()
    stored_session = db_session.get(EventSession, session.id)
    assert completion_code.status == CompletionCodeStatus.ISSUED.value
    assert stored_session is not None
    assert stored_session.status == SessionStatus.COMPLETED.value
    assert stored_session.completed_at is not None


def test_get_completion_code_success(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    session, code = _complete_session(client, db_session, event_factory)

    response = client.get(f"/api/sessions/{session.id}/completion-code")

    assert response.status_code == 200
    data = response.json()
    assert data["completionCode"]["code"] == code
    assert data["completionCode"]["status"] == "issued"
    assert data["completionCode"]["issuedAt"]


def test_completion_code_not_found_for_incomplete_session(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)

    response = client.get(f"/api/sessions/{session.id}/completion-code")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMPLETION_CODE_NOT_FOUND"
