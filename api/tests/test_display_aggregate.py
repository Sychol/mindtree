from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.enums import CompletionCodeStatus, SessionStatus
from app.models.keyword import Keyword
from app.models.reply import Reply
from app.models.risk import RiskFlag
from app.services.display_aggregate import build_display_snapshot
from tests.test_cards_api import _card, _session


def _keyword(
    db_session: Session,
    *,
    source: MindCard | Reply,
    text: str,
    category: str,
    weight: Decimal | str = "1",
    status: str = "active",
) -> Keyword:
    keyword = Keyword(
        event_id=source.event_id,
        source_type="mind_card" if isinstance(source, MindCard) else "reply",
        source_id=source.id,
        keyword_text=f"{text}-raw",
        normalized_keyword=text,
        category=category,
        weight=Decimal(weight),
        status=status,
        extraction_method="fallback",
    )
    db_session.add(keyword)
    db_session.commit()
    db_session.refresh(keyword)
    return keyword


def _reply(db_session: Session, *, card: MindCard, session_id) -> Reply:
    reply = Reply(
        event_id=card.event_id,
        session_id=session_id,
        target_card_id=card.id,
        reply_type="comfort",
        content_raw="reply raw content must not leak",
        safety_status="safe",
        public_status="public",
    )
    db_session.add(reply)
    db_session.commit()
    db_session.refresh(reply)
    return reply


def test_display_snapshot_aggregates_active_public_keywords(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    peer_session = _session(db_session, event, status=SessionStatus.CARD_CREATED.value)
    card = _card(db_session, event, session, content="raw card content must not leak")
    reply = _reply(db_session, card=card, session_id=peer_session.id)

    _keyword(db_session, source=card, text="긴장", category="mind_signal", weight="4")
    _keyword(db_session, source=card, text="긴장", category="mind_signal", weight="6")
    _keyword(db_session, source=reply, text="쉼", category="support", weight="7")
    _keyword(db_session, source=reply, text="호흡", category="coping", weight="3")

    db_session.add(
        CompletionCode(
            event_id=event.id,
            session_id=session.id,
            code=f"TREE-{uuid4().hex[:6].upper()}",
            status=CompletionCodeStatus.ISSUED.value,
        )
    )
    db_session.add(
        CompletionCode(
            event_id=event.id,
            session_id=peer_session.id,
            code=f"TREE-{uuid4().hex[:6].upper()}",
            status=CompletionCodeStatus.VOID.value,
        )
    )
    db_session.commit()

    snapshot = build_display_snapshot(db_session, event.slug)

    assert snapshot.participantCount == 2
    assert snapshot.completedCount == 1
    assert [(item.text, item.weight) for item in snapshot.topMindKeywords] == [("긴장", 10.0)]
    assert [(item.text, item.weight) for item in snapshot.topSupportKeywords] == [
        ("쉼", 7.0),
        ("호흡", 3.0),
    ]
    assert {item.text for item in snapshot.cloudKeywords} == {"긴장", "쉼", "호흡"}


def test_display_snapshot_excludes_hidden_excluded_and_non_public_sources(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    safe_session = _session(db_session, event)
    review_session = _session(db_session, event)
    pending_session = _session(db_session, event)
    safe_card = _card(db_session, event, safe_session)
    review_card = _card(
        db_session,
        event,
        review_session,
        safety_status="review",
        public_status="public",
    )
    pending_card = _card(
        db_session,
        event,
        pending_session,
        safety_status="safe",
        public_status="pending",
    )

    _keyword(db_session, source=safe_card, text="표시", category="support", weight="2")
    _keyword(db_session, source=safe_card, text="숨김", category="support", status="hidden")
    _keyword(db_session, source=safe_card, text="제외", category="support", status="excluded")
    _keyword(db_session, source=review_card, text="검토", category="support")
    _keyword(db_session, source=pending_card, text="대기", category="support")

    snapshot = build_display_snapshot(db_session, event.slug)

    assert [item.text for item in snapshot.cloudKeywords] == ["표시"]


def test_display_snapshot_excludes_restricted_and_crisis_sources(db_session: Session, event_factory) -> None:
    event = event_factory()
    allowed_session = _session(db_session, event)
    restricted_session = _session(db_session, event)
    crisis_session = _session(db_session, event)
    allowed_card = _card(db_session, event, allowed_session)
    restricted_card = _card(db_session, event, restricted_session)
    crisis_card = _card(db_session, event, crisis_session)

    restricted_flag = db_session.execute(
        select(RiskFlag).where(RiskFlag.session_id == restricted_session.id)
    ).scalar_one()
    restricted_flag.public_restriction = True
    crisis_flag = db_session.execute(select(RiskFlag).where(RiskFlag.session_id == crisis_session.id)).scalar_one()
    crisis_flag.crisis_expression_detected = True
    db_session.add_all([restricted_flag, crisis_flag])
    db_session.commit()

    _keyword(db_session, source=allowed_card, text="안전", category="recovery")
    _keyword(db_session, source=restricted_card, text="제한", category="recovery")
    _keyword(db_session, source=crisis_card, text="위기", category="recovery")

    snapshot = build_display_snapshot(db_session, event.slug)

    assert [item.text for item in snapshot.cloudKeywords] == ["안전"]


def test_display_snapshot_limits_cloud_keywords_to_forty(db_session: Session, event_factory) -> None:
    event = event_factory()
    session = _session(db_session, event)
    card = _card(db_session, event, session)
    for index in range(45):
        _keyword(
            db_session,
            source=card,
            text=f"키워드{index:02d}",
            category="neutral",
            weight=str(100 - index),
        )

    snapshot = build_display_snapshot(db_session, event.slug)

    assert len(snapshot.cloudKeywords) == 40
    assert snapshot.cloudKeywords[0].text == "키워드00"
    assert snapshot.cloudKeywords[-1].text == "키워드39"
