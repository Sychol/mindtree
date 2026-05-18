from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.completion import CompletionCode
from app.models.enums import (
    CompletionCodeStatus,
    ContentOrigin,
    KeywordExtractionMethod,
    KeywordSourceType,
)
from app.models.keyword import Keyword
from app.services.display_aggregate import build_display_snapshot
from tests.test_cards_api import _card, _session
from tests.test_display_api_privacy import FORBIDDEN_TOKENS


def _manual_keyword(
    db_session: Session,
    event_id,
    *,
    text: str,
    category: str = "recovery",
    status: str = "active",
    weight: str = "5",
    origin: str = ContentOrigin.ADMIN_MANUAL.value,
) -> Keyword:
    keyword = Keyword(
        event_id=event_id,
        source_type=KeywordSourceType.ADMIN_MANUAL.value,
        source_id=None,
        keyword_text=text,
        normalized_keyword=text,
        category=category,
        weight=Decimal(weight),
        status=status,
        extraction_method=KeywordExtractionMethod.ADMIN.value,
        origin=origin,
        origin_tag="운영자추가",
        created_by_admin_id=None,
    )
    db_session.add(keyword)
    db_session.commit()
    db_session.refresh(keyword)
    return keyword


def test_active_manual_keyword_is_included_in_display_snapshot(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    _manual_keyword(db_session, event.id, text="쉼", category="recovery", weight="5")

    snapshot = build_display_snapshot(db_session, event.slug)

    assert snapshot.participantCount == 0
    assert snapshot.completedCount == 0
    assert [(item.text, item.weight, item.category) for item in snapshot.cloudKeywords] == [
        ("쉼", 5.0, "recovery")
    ]
    assert [(item.text, item.weight) for item in snapshot.topSupportKeywords] == [("쉼", 5.0)]


def test_hidden_and_excluded_manual_keywords_are_excluded(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    _manual_keyword(db_session, event.id, text="표시", status="active")
    _manual_keyword(db_session, event.id, text="숨김", status="hidden")
    _manual_keyword(db_session, event.id, text="제외", status="excluded")

    snapshot = build_display_snapshot(db_session, event.slug)

    assert [item.text for item in snapshot.cloudKeywords] == ["표시"]


def test_participant_keyword_conditions_still_apply_with_manual_keywords(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    safe_card = _card(db_session, event, session)
    pending_card = _card(db_session, event, _session(db_session, event), public_status="pending")
    db_session.add_all(
        [
            Keyword(
                event_id=event.id,
                source_type="mind_card",
                source_id=safe_card.id,
                keyword_text="긴장",
                normalized_keyword="긴장",
                category="mind_signal",
                weight=Decimal("4"),
                status="active",
                extraction_method="fallback",
            ),
            Keyword(
                event_id=event.id,
                source_type="mind_card",
                source_id=pending_card.id,
                keyword_text="대기",
                normalized_keyword="대기",
                category="support",
                weight=Decimal("9"),
                status="active",
                extraction_method="fallback",
            ),
        ]
    )
    db_session.commit()
    _manual_keyword(db_session, event.id, text="쉼", category="recovery", weight="5")

    snapshot = build_display_snapshot(db_session, event.slug)

    assert {item.text for item in snapshot.cloudKeywords} == {"긴장", "쉼"}
    assert "대기" not in {item.text for item in snapshot.cloudKeywords}


def test_manual_keyword_does_not_change_counts(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    db_session.add(
        CompletionCode(
            event_id=event.id,
            session_id=session.id,
            code=f"TREE-{uuid4().hex[:6].upper()}",
            status=CompletionCodeStatus.ISSUED.value,
        )
    )
    db_session.commit()

    before = build_display_snapshot(db_session, event.slug)
    _manual_keyword(db_session, event.id, text="쉼")
    after = build_display_snapshot(db_session, event.slug)

    assert before.participantCount == 1
    assert before.completedCount == 1
    assert after.participantCount == 1
    assert after.completedCount == 1


def test_display_snapshot_response_does_not_expose_manual_origin_fields(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    _manual_keyword(db_session, event.id, text="쉼")

    response = client.get(f"/api/events/{event.slug}/display/snapshot")

    assert response.status_code == 200
    payload = response.json()
    assert payload["cloudKeywords"] == [{"text": "쉼", "weight": 5.0, "category": "recovery"}]
    response_text = response.text
    assert "origin" not in response_text
    assert "originTag" not in response_text
    assert "createdByAdminId" not in response_text
    for token in FORBIDDEN_TOKENS:
        assert token not in response_text
