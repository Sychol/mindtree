from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_token
from app.models.consent import ConsentLog
from app.models.session import Session as EventSession


def _required_consent_payload(consent_version: str = "v1") -> dict:
    return {
        "consentVersion": consent_version,
        "acceptedItems": {
            "eventIsNotDiagnosis": True,
            "anonymousKeywordDisplay": True,
            "cardMayBeShownAnonymously": True,
            "noIdentifyingInfo": True,
            "adminModeration": True,
        },
    }


def _create_session(client: TestClient, event_slug: str, resume_token: str | None = None) -> dict:
    payload: dict = {
        "clientMeta": {
            "device": "mobile",
            "timezone": "Asia/Seoul",
            "ignored": "do-not-store",
        }
    }
    if resume_token is not None:
        payload["resumeToken"] = resume_token

    response = client.post(f"/api/events/{event_slug}/sessions", json=payload)
    assert response.status_code == 200
    return response.json()


def _consent_logs(db_session: Session, session_id: UUID) -> list[ConsentLog]:
    return list(
        db_session.execute(
            select(ConsentLog).where(ConsentLog.session_id == session_id)
        ).scalars()
    )


def test_create_session_without_resume_token(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()

    data = _create_session(client, event.slug)

    assert data["session"]["eventSlug"] == event.slug
    assert data["session"]["status"] == "created"
    assert data["session"]["lastStep"] == "landing"
    assert data["resumeToken"]

    db_session.expire_all()
    stored_session = db_session.get(EventSession, UUID(data["session"]["id"]))
    assert stored_session is not None
    assert stored_session.resume_token_hash != data["resumeToken"]
    assert stored_session.anonymous_key_hash != data["resumeToken"]
    assert stored_session.resume_token_hash == hash_token(data["resumeToken"])
    assert stored_session.client_meta == {
        "device": "mobile",
        "timezone": "Asia/Seoul",
    }


def test_same_resume_token_restores_existing_session(
    client: TestClient,
    event_factory,
) -> None:
    event = event_factory()
    resume_token = "client-generated-token"

    first = _create_session(client, event.slug, resume_token)
    second = _create_session(client, event.slug, resume_token)

    assert second["session"]["id"] == first["session"]["id"]
    assert second["resumeToken"] == resume_token


def test_different_resume_tokens_create_different_sessions(
    client: TestClient,
    event_factory,
) -> None:
    event = event_factory()

    first = _create_session(client, event.slug, "client-generated-token-1")
    second = _create_session(client, event.slug, "client-generated-token-2")

    assert second["session"]["id"] != first["session"]["id"]


def test_get_session_state_returns_progress(
    client: TestClient,
    event_factory,
) -> None:
    event = event_factory()
    created = _create_session(client, event.slug)

    response = client.get(f"/api/sessions/{created['session']['id']}")

    assert response.status_code == 200
    data = response.json()
    assert data["session"]["eventSlug"] == event.slug
    assert data["progress"] == {
        "consentAccepted": False,
        "questionsCompleted": False,
        "summaryViewed": False,
        "mindCardCount": 0,
        "selectedCard": False,
        "replyCreated": False,
        "completionCodeIssued": False,
    }


def test_get_missing_session_returns_not_found(client: TestClient) -> None:
    response = client.get(f"/api/sessions/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"


def test_accept_consent_transitions_session_and_hashes_request_metadata(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    created = _create_session(client, event.slug)
    session_id = UUID(created["session"]["id"])

    response = client.post(
        f"/api/sessions/{session_id}/consent",
        json=_required_consent_payload(),
        headers={"User-Agent": "phase03-test-agent"},
    )

    assert response.status_code == 200
    assert response.json()["sessionStatus"] == "consented"

    db_session.expire_all()
    stored_session = db_session.get(EventSession, session_id)
    assert stored_session is not None
    assert stored_session.status == "consented"
    assert stored_session.last_step == "questions"

    logs = _consent_logs(db_session, session_id)
    assert len(logs) == 1
    assert logs[0].ip_hash
    assert logs[0].ip_hash != "testclient"
    assert logs[0].user_agent_hash
    assert logs[0].user_agent_hash != "phase03-test-agent"


def test_accept_consent_is_idempotent(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    created = _create_session(client, event.slug)
    session_id = UUID(created["session"]["id"])
    payload = _required_consent_payload()

    first = client.post(f"/api/sessions/{session_id}/consent", json=payload)
    second = client.post(f"/api/sessions/{session_id}/consent", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    db_session.expire_all()
    assert len(_consent_logs(db_session, session_id)) == 1


def test_accept_consent_missing_required_item_returns_bad_request(
    client: TestClient,
    event_factory,
) -> None:
    event = event_factory()
    created = _create_session(client, event.slug)
    payload = _required_consent_payload()
    del payload["acceptedItems"]["adminModeration"]

    response = client.post(
        f"/api/sessions/{created['session']['id']}/consent",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_accept_consent_false_required_item_returns_bad_request(
    client: TestClient,
    event_factory,
) -> None:
    event = event_factory()
    created = _create_session(client, event.slug)
    payload = _required_consent_payload()
    payload["acceptedItems"]["adminModeration"] = False

    response = client.post(
        f"/api/sessions/{created['session']['id']}/consent",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"


def test_accept_consent_version_mismatch_returns_bad_request(
    client: TestClient,
    event_factory,
) -> None:
    event = event_factory(consent_version="v2")
    created = _create_session(client, event.slug)

    response = client.post(
        f"/api/sessions/{created['session']['id']}/consent",
        json=_required_consent_payload("v1"),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "BAD_REQUEST"
