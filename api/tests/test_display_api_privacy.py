from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.keyword import Keyword
from tests.test_cards_api import _card, _session


FORBIDDEN_TOKENS = [
    "content_raw",
    "contentRaw",
    "content_redacted",
    "contentRedacted",
    "session_id",
    "sessionId",
    "resumeToken",
    "completionCode",
    "completion_code",
    "scale_scores",
    "scaleScores",
    "risk_flags",
    "riskFlags",
    "safety_status",
    "public_status",
    "moderation_reason",
    "reviewed_by",
]


def test_display_snapshot_api_returns_privacy_safe_payload(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session, content="private source sentence should never be returned")
    db_session.add(
        Keyword(
            event_id=event.id,
            source_type="mind_card",
            source_id=card.id,
            keyword_text="raw keyword should not be used",
            normalized_keyword="쉼",
            category="support",
            weight=Decimal("3"),
            status="active",
            extraction_method="fallback",
        )
    )
    db_session.commit()

    response = client.get(f"/api/events/{event.slug}/display/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "eventSlug",
        "participantCount",
        "completedCount",
        "topMindKeywords",
        "topSupportKeywords",
        "cloudKeywords",
        "generatedAt",
    }
    response_text = response.text
    assert "private source sentence" not in response_text
    assert "raw keyword should not be used" not in response_text
    for token in FORBIDDEN_TOKENS:
        assert token not in response_text


def test_display_snapshot_api_returns_empty_keyword_lists(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.get(f"/api/events/{event.slug}/display/snapshot")

    assert response.status_code == 200
    assert response.json()["topMindKeywords"] == []
    assert response.json()["topSupportKeywords"] == []
    assert response.json()["cloudKeywords"] == []
