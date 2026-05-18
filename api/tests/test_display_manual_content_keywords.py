from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.enums import CompletionCodeStatus, ContentOrigin
from app.models.keyword import Keyword
from app.models.reply import Reply
from app.services.display_aggregate import build_display_snapshot
from tests.admin_test_utils import create_admin
from tests.test_cards_api import _session
from tests.test_display_api_privacy import FORBIDDEN_TOKENS


def _manual_card(db_session: Session, event_id, *, public_status: str = "public") -> MindCard:
    admin = create_admin(db_session)
    card = MindCard(
        event_id=event_id,
        session_id=None,
        prompt_type="to_colleague",
        content_raw="manual card raw must not leak",
        safety_status="safe",
        public_status=public_status,
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag="ops",
        created_by_admin_id=admin.id,
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


def _manual_reply(db_session: Session, event_id, *, public_status: str = "public") -> Reply:
    admin = create_admin(db_session)
    reply = Reply(
        event_id=event_id,
        session_id=None,
        target_card_id=None,
        reply_type="comfort",
        content_raw="manual reply raw must not leak",
        safety_status="safe",
        public_status=public_status,
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag="ops",
        created_by_admin_id=admin.id,
    )
    db_session.add(reply)
    db_session.commit()
    db_session.refresh(reply)
    return reply


def _keyword(
    db_session: Session,
    *,
    event_id,
    source_type: str,
    source_id,
    text: str,
    category: str = "support",
    status: str = "active",
) -> Keyword:
    keyword = Keyword(
        event_id=event_id,
        source_type=source_type,
        source_id=source_id,
        keyword_text=text,
        normalized_keyword=text,
        category=category,
        weight=Decimal("3"),
        status=status,
        extraction_method="fallback",
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag="ops",
    )
    db_session.add(keyword)
    db_session.commit()
    db_session.refresh(keyword)
    return keyword


def test_manual_card_and_reply_keywords_are_in_display_snapshot(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    card = _manual_card(db_session, event.id)
    reply = _manual_reply(db_session, event.id)
    _keyword(db_session, event_id=event.id, source_type="mind_card", source_id=card.id, text="manual-card")
    _keyword(db_session, event_id=event.id, source_type="reply", source_id=reply.id, text="manual-reply")

    snapshot = build_display_snapshot(db_session, event.slug)

    assert snapshot.participantCount == 0
    assert snapshot.completedCount == 0
    assert {item.text for item in snapshot.cloudKeywords} == {"manual-card", "manual-reply"}


def test_hidden_or_excluded_manual_sources_are_excluded_from_display(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    visible_card = _manual_card(db_session, event.id)
    hidden_card = _manual_card(db_session, event.id, public_status="hidden")
    visible_reply = _manual_reply(db_session, event.id)
    excluded_reply = _manual_reply(db_session, event.id, public_status="excluded")
    _keyword(db_session, event_id=event.id, source_type="mind_card", source_id=visible_card.id, text="visible-card")
    _keyword(db_session, event_id=event.id, source_type="mind_card", source_id=hidden_card.id, text="hidden-card")
    _keyword(db_session, event_id=event.id, source_type="reply", source_id=visible_reply.id, text="visible-reply")
    _keyword(db_session, event_id=event.id, source_type="reply", source_id=excluded_reply.id, text="excluded-reply")

    snapshot = build_display_snapshot(db_session, event.slug)

    assert {item.text for item in snapshot.cloudKeywords} == {"visible-card", "visible-reply"}


def test_manual_content_does_not_increase_participant_or_completed_counts(
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
    card = _manual_card(db_session, event.id)
    reply = _manual_reply(db_session, event.id)
    _keyword(db_session, event_id=event.id, source_type="mind_card", source_id=card.id, text="manual-card")
    _keyword(db_session, event_id=event.id, source_type="reply", source_id=reply.id, text="manual-reply")

    after = build_display_snapshot(db_session, event.slug)

    assert before.participantCount == 1
    assert before.completedCount == 1
    assert after.participantCount == 1
    assert after.completedCount == 1


def test_display_snapshot_response_does_not_expose_manual_content_private_fields(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    card = _manual_card(db_session, event.id)
    _keyword(db_session, event_id=event.id, source_type="mind_card", source_id=card.id, text="manual-card")

    response = client.get(f"/api/events/{event.slug}/display/snapshot")

    assert response.status_code == 200
    response_text = response.text
    assert "manual card raw must not leak" not in response_text
    assert "origin" not in response_text
    assert "originTag" not in response_text
    assert "createdByAdminId" not in response_text
    for token in FORBIDDEN_TOKENS:
        assert token not in response_text
