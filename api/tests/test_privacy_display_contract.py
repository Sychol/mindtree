from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.keyword import Keyword
from app.models.risk import RiskFlag
from app.schemas.display import DisplayKeyword, DisplaySnapshotResponse
from app.services.display import snapshot_to_event
from tests.test_cards_api import _card, _session

FORBIDDEN_DISPLAY_TOKENS = [
    "content_raw",
    "contentRaw",
    "content_redacted",
    "contentRedacted",
    "mindCardContent",
    "replyContent",
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
    "admin",
]


def _assert_privacy_safe(payload: str) -> None:
    for token in FORBIDDEN_DISPLAY_TOKENS:
        assert token not in payload


def _keyword(
    db_session: Session,
    event_id,
    card_id,
    *,
    normalized: str,
    status: str = "active",
    category: str = "support",
) -> None:
    db_session.add(
        Keyword(
            event_id=event_id,
            source_type="mind_card",
            source_id=card_id,
            keyword_text=f"raw-{normalized}",
            normalized_keyword=normalized,
            category=category,
            weight=Decimal("2"),
            status=status,
            extraction_method="fallback",
        )
    )


def test_display_snapshot_contract_excludes_private_fields_and_hidden_sources(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    visible_session = _session(db_session, event)
    hidden_session = _session(db_session, event)
    excluded_session = _session(db_session, event)
    restricted_session = _session(db_session, event)

    visible_card = _card(db_session, event, visible_session, content="private visible source")
    hidden_card = _card(db_session, event, hidden_session, content="private hidden source")
    excluded_card = _card(db_session, event, excluded_session, content="private excluded source")
    restricted_card = _card(db_session, event, restricted_session, content="private restricted source")

    risk = db_session.query(RiskFlag).filter(RiskFlag.session_id == restricted_session.id).one()
    risk.public_restriction = True
    db_session.add(risk)

    _keyword(db_session, event.id, visible_card.id, normalized="visible-safe")
    _keyword(db_session, event.id, hidden_card.id, normalized="hidden-keyword", status="hidden")
    _keyword(db_session, event.id, excluded_card.id, normalized="excluded-keyword", status="excluded")
    _keyword(db_session, event.id, restricted_card.id, normalized="restricted-keyword")
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
    _assert_privacy_safe(response_text)
    assert "visible-safe" in response_text
    assert "private visible source" not in response_text
    assert "hidden-keyword" not in response_text
    assert "excluded-keyword" not in response_text
    assert "restricted-keyword" not in response_text


def test_sse_keyword_snapshot_contract_excludes_private_fields() -> None:
    snapshot = DisplaySnapshotResponse(
        eventSlug="fire-expo-2026",
        participantCount=2,
        completedCount=1,
        topMindKeywords=[DisplayKeyword(text="steady", weight=2)],
        topSupportKeywords=[],
        cloudKeywords=[DisplayKeyword(text="steady", weight=2, category="support")],
        generatedAt=datetime.now(timezone.utc),
    )

    payload = snapshot_to_event(snapshot)

    assert "event: keyword_snapshot" in payload
    assert "steady" in payload
    _assert_privacy_safe(payload)
