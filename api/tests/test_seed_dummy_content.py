from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.enums import (
    ContentOrigin,
    KeywordExtractionMethod,
    KeywordSourceType,
    PublicStatus,
    SafetyStatus,
)
from app.models.keyword import Keyword
from app.models.reply import Reply
from app.models.session import Session as EventSession
from app.scripts.seed_dummy_content import seed_dummy_content
from app.services.display_aggregate import build_display_snapshot
from tests.test_display_api_privacy import FORBIDDEN_TOKENS


def _count(db_session: Session, model, event_id) -> int:
    return int(
        db_session.execute(
            select(func.count(model.id)).where(model.event_id == event_id)
        ).scalar_one()
        or 0
    )


def _system_seed_count(
    db_session: Session,
    model,
    event_id,
    *,
    batch_label: str,
) -> int:
    return int(
        db_session.execute(
            select(func.count(model.id)).where(
                model.event_id == event_id,
                model.origin == ContentOrigin.SYSTEM_SEED.value,
                model.origin_tag == batch_label,
            )
        ).scalar_one()
        or 0
    )


def test_seed_dummy_content_missing_event_fails(db_session: Session) -> None:
    with pytest.raises(RuntimeError, match="Event not found"):
        seed_dummy_content(
            db_session,
            event_slug="missing-event",
            cards=1,
            replies=1,
            keywords=1,
            batch_label="dummy-content-test",
            mode="missing",
        )


def test_seed_dummy_content_creates_cold_start_content_without_participant_flow(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()

    result = seed_dummy_content(
        db_session,
        event_slug=event.slug,
        cards=100,
        replies=100,
        keywords=100,
        batch_label="dummy-content-test",
        mode="missing",
    )

    assert result.cards_created == 100
    assert result.replies_created == 100
    assert result.keywords_created == 100
    assert _system_seed_count(db_session, MindCard, event.id, batch_label="dummy-content-test") == 100
    assert _system_seed_count(db_session, Reply, event.id, batch_label="dummy-content-test") == 100
    assert _system_seed_count(db_session, Keyword, event.id, batch_label="dummy-content-test") == 100

    cards = db_session.execute(select(MindCard).where(MindCard.event_id == event.id)).scalars().all()
    replies = db_session.execute(select(Reply).where(Reply.event_id == event.id)).scalars().all()
    keywords = db_session.execute(select(Keyword).where(Keyword.event_id == event.id)).scalars().all()

    assert all(card.session_id is None for card in cards)
    assert all(card.origin == ContentOrigin.SYSTEM_SEED.value for card in cards)
    assert all(card.origin_tag == "dummy-content-test" for card in cards)
    assert all(card.safety_status == SafetyStatus.SAFE.value for card in cards)
    assert all(card.public_status == PublicStatus.PUBLIC.value for card in cards)

    assert all(reply.session_id is None for reply in replies)
    assert all(reply.target_card_id is None for reply in replies)
    assert all(reply.origin == ContentOrigin.SYSTEM_SEED.value for reply in replies)
    assert all(reply.origin_tag == "dummy-content-test" for reply in replies)
    assert all(reply.safety_status == SafetyStatus.SAFE.value for reply in replies)
    assert all(reply.public_status == PublicStatus.PUBLIC.value for reply in replies)

    assert all(keyword.source_type == KeywordSourceType.ADMIN_MANUAL.value for keyword in keywords)
    assert all(keyword.source_id is None for keyword in keywords)
    assert all(keyword.origin == ContentOrigin.SYSTEM_SEED.value for keyword in keywords)
    assert all(keyword.origin_tag == "dummy-content-test" for keyword in keywords)
    assert all(keyword.extraction_method == KeywordExtractionMethod.ADMIN.value for keyword in keywords)
    assert len({keyword.normalized_keyword for keyword in keywords}) < len(keywords)

    assert _count(db_session, EventSession, event.id) == 0
    assert _count(db_session, Answer, event.id) == 0
    assert _count(db_session, CompletionCode, event.id) == 0

    snapshot = build_display_snapshot(db_session, event.slug)
    assert snapshot.participantCount == 0
    assert snapshot.completedCount == 0
    assert snapshot.cloudKeywords


def test_seed_dummy_content_missing_mode_is_idempotent(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()

    first = seed_dummy_content(
        db_session,
        event_slug=event.slug,
        cards=100,
        replies=100,
        keywords=100,
        batch_label="dummy-content-idempotent",
        mode="missing",
    )
    second = seed_dummy_content(
        db_session,
        event_slug=event.slug,
        cards=100,
        replies=100,
        keywords=100,
        batch_label="dummy-content-idempotent",
        mode="missing",
    )

    assert first.cards_created == 100
    assert first.replies_created == 100
    assert first.keywords_created == 100
    assert second.cards_created == 0
    assert second.replies_created == 0
    assert second.keywords_created == 0
    assert second.cards_skipped_existing == 100
    assert second.replies_skipped_existing == 100
    assert second.keywords_skipped_existing == 100
    assert _system_seed_count(db_session, MindCard, event.id, batch_label="dummy-content-idempotent") == 100
    assert _system_seed_count(db_session, Reply, event.id, batch_label="dummy-content-idempotent") == 100
    assert _system_seed_count(db_session, Keyword, event.id, batch_label="dummy-content-idempotent") == 100


def test_seed_dummy_content_force_only_excludes_same_system_seed_batch(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_dummy_content(
        db_session,
        event_slug=event.slug,
        cards=3,
        replies=3,
        keywords=3,
        batch_label="dummy-content-force",
        mode="missing",
    )
    old_card_ids = [
        card.id
        for card in db_session.execute(
            select(MindCard).where(
                MindCard.event_id == event.id,
                MindCard.origin == ContentOrigin.SYSTEM_SEED.value,
                MindCard.origin_tag == "dummy-content-force",
            )
        ).scalars()
    ]
    old_reply_ids = [
        reply.id
        for reply in db_session.execute(
            select(Reply).where(
                Reply.event_id == event.id,
                Reply.origin == ContentOrigin.SYSTEM_SEED.value,
                Reply.origin_tag == "dummy-content-force",
            )
        ).scalars()
    ]
    old_keyword_ids = [
        keyword.id
        for keyword in db_session.execute(
            select(Keyword).where(
                Keyword.event_id == event.id,
                Keyword.origin == ContentOrigin.SYSTEM_SEED.value,
                Keyword.origin_tag == "dummy-content-force",
            )
        ).scalars()
    ]

    participant_card = MindCard(
        event_id=event.id,
        session_id=None,
        prompt_type="stress_memory",
        content_raw="real participant origin content",
        safety_status=SafetyStatus.SAFE.value,
        public_status=PublicStatus.PUBLIC.value,
        origin=ContentOrigin.PARTICIPANT.value,
        origin_tag="dummy-content-force",
    )
    other_batch_card = MindCard(
        event_id=event.id,
        session_id=None,
        prompt_type="stress_memory",
        content_raw="other system seed batch content",
        safety_status=SafetyStatus.SAFE.value,
        public_status=PublicStatus.PUBLIC.value,
        origin=ContentOrigin.SYSTEM_SEED.value,
        origin_tag="other-batch",
    )
    admin_manual_reply = Reply(
        event_id=event.id,
        session_id=None,
        target_card_id=None,
        reply_type="comfort",
        content_raw="admin manual reply",
        safety_status=SafetyStatus.SAFE.value,
        public_status=PublicStatus.PUBLIC.value,
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag="dummy-content-force",
    )
    db_session.add_all([participant_card, other_batch_card, admin_manual_reply])
    db_session.commit()

    result = seed_dummy_content(
        db_session,
        event_slug=event.slug,
        cards=3,
        replies=3,
        keywords=3,
        batch_label="dummy-content-force",
        mode="force",
    )

    assert result.force_excluded_cards == 3
    assert result.force_excluded_replies == 3
    assert result.force_excluded_keywords == 3
    assert result.cards_created == 3
    assert result.replies_created == 3
    assert result.keywords_created == 3

    for card_id in old_card_ids:
        old_card = db_session.get(MindCard, card_id)
        assert old_card is not None
        assert old_card.safety_status == SafetyStatus.EXCLUDE.value
        assert old_card.public_status == PublicStatus.EXCLUDED.value
    for reply_id in old_reply_ids:
        old_reply = db_session.get(Reply, reply_id)
        assert old_reply is not None
        assert old_reply.safety_status == SafetyStatus.EXCLUDE.value
        assert old_reply.public_status == PublicStatus.EXCLUDED.value
    for keyword_id in old_keyword_ids:
        old_keyword = db_session.get(Keyword, keyword_id)
        assert old_keyword is not None
        assert old_keyword.status == "excluded"

    db_session.refresh(participant_card)
    db_session.refresh(other_batch_card)
    db_session.refresh(admin_manual_reply)
    assert participant_card.public_status == PublicStatus.PUBLIC.value
    assert other_batch_card.public_status == PublicStatus.PUBLIC.value
    assert admin_manual_reply.public_status == PublicStatus.PUBLIC.value

    active_cards = db_session.execute(
        select(MindCard).where(
            MindCard.event_id == event.id,
            MindCard.origin == ContentOrigin.SYSTEM_SEED.value,
            MindCard.origin_tag == "dummy-content-force",
            MindCard.public_status == PublicStatus.PUBLIC.value,
        )
    ).scalars().all()
    active_keywords = db_session.execute(
        select(Keyword).where(
            Keyword.event_id == event.id,
            Keyword.origin == ContentOrigin.SYSTEM_SEED.value,
            Keyword.origin_tag == "dummy-content-force",
            Keyword.status == "active",
        )
    ).scalars().all()
    assert len(active_cards) == 3
    assert len(active_keywords) == 3


def test_system_seed_direct_keywords_are_displayed_and_status_filtered(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_dummy_content(
        db_session,
        event_slug=event.slug,
        cards=0,
        replies=0,
        keywords=3,
        batch_label="dummy-content-display",
        mode="missing",
    )
    db_session.add_all(
        [
            Keyword(
                event_id=event.id,
                source_type=KeywordSourceType.ADMIN_MANUAL.value,
                source_id=None,
                keyword_text="hidden seed",
                normalized_keyword="hidden-seed",
                category="support",
                weight=Decimal("30"),
                status="hidden",
                extraction_method=KeywordExtractionMethod.ADMIN.value,
                origin=ContentOrigin.SYSTEM_SEED.value,
                origin_tag="dummy-content-display",
            ),
            Keyword(
                event_id=event.id,
                source_type=KeywordSourceType.ADMIN_MANUAL.value,
                source_id=None,
                keyword_text="excluded seed",
                normalized_keyword="excluded-seed",
                category="support",
                weight=Decimal("30"),
                status="excluded",
                extraction_method=KeywordExtractionMethod.ADMIN.value,
                origin=ContentOrigin.SYSTEM_SEED.value,
                origin_tag="dummy-content-display",
            ),
        ]
    )
    db_session.commit()

    snapshot = build_display_snapshot(db_session, event.slug)
    cloud_texts = {item.text for item in snapshot.cloudKeywords}

    assert cloud_texts
    assert "hidden-seed" not in cloud_texts
    assert "excluded-seed" not in cloud_texts


def test_display_snapshot_response_does_not_expose_seed_private_fields(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed_dummy_content(
        db_session,
        event_slug=event.slug,
        cards=2,
        replies=2,
        keywords=2,
        batch_label="dummy-content-private",
        mode="missing",
    )

    response = client.get(f"/api/events/{event.slug}/display/snapshot")

    assert response.status_code == 200
    response_text = response.text
    assert "origin" not in response_text
    assert "originTag" not in response_text
    assert "createdByAdminId" not in response_text
    assert "dummy-content-private" not in response_text
    for token in FORBIDDEN_TOKENS:
        assert token not in response_text
