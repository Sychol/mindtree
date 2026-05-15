import json
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.answer import Answer
from app.models.question import Question
from app.models.session import Session as EventSession
from app.scripts.seed_questions import (
    RULE_VERSION,
    SeedValidationError,
    load_questions_seed,
    seed_questions_for_event,
)

ROOT = Path(__file__).resolve().parents[2]


def test_questions_seed_json_is_valid_utf8() -> None:
    path = ROOT / "docs" / "data" / "questions_fire_expo_2026_final_260515.json"

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    question_nos = [question["questionNo"] for question in data["questions"]]

    assert data["metadata"]["encoding"] == "utf-8"
    assert data["metadata"]["questionCount"] == 61
    assert data["metadata"]["ruleVersion"] == RULE_VERSION
    assert sorted(question_nos) == list(range(1, 62))

    scale_counts = {}
    for question in data["questions"]:
        scale_counts[question["scaleCode"]] = scale_counts.get(question["scaleCode"], 0) + 1
    assert scale_counts == {
        "profile": 14,
        "kmies": 6,
        "phq9": 9,
        "pcl5": 20,
        "kscs": 12,
    }
    by_no = {question["questionNo"]: question for question in data["questions"]}
    assert by_no[29]["questionKey"] == "phq9_09"
    assert by_no[29]["riskTrigger"]["type"] == "phq9_item9_positive"


def test_seed_questions_upserts_61_questions_without_duplicates(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    seed = load_questions_seed()

    first = seed_questions_for_event(db_session, event.slug, seed)
    second = seed_questions_for_event(db_session, event.slug, seed)

    count = db_session.execute(
        select(Question).where(Question.event_id == event.id)
    ).scalars().all()

    assert first == {"created": 61, "updated": 0, "deletedStale": 0, "total": 61}
    assert second == {"created": 0, "updated": 61, "deletedStale": 0, "total": 61}
    assert len(count) == 61


def test_seed_questions_deletes_stale_questions_without_answers(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    stale = Question(
        event_id=event.id,
        question_no=77,
        scale_code="kscs",
        question_key="old_kscs_77",
        title="stale question",
        question_type="likert",
        options=[],
        score_map={},
        required=True,
        display_order=77,
    )
    db_session.add(stale)
    db_session.commit()

    result = seed_questions_for_event(db_session, event.slug)
    questions = db_session.execute(
        select(Question).where(Question.event_id == event.id).order_by(Question.question_no)
    ).scalars().all()

    assert result == {"created": 61, "updated": 0, "deletedStale": 1, "total": 61}
    assert [question.question_no for question in questions] == list(range(1, 62))


def test_seed_questions_blocks_stale_questions_with_answers(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    stale = Question(
        event_id=event.id,
        question_no=77,
        scale_code="kscs",
        question_key="old_kscs_77",
        title="stale question",
        question_type="likert",
        options=[],
        score_map={},
        required=True,
        display_order=77,
    )
    db_session.add(stale)
    db_session.flush()
    session = EventSession(
        event_id=event.id,
        anonymous_key_hash=f"anon-{uuid4()}",
        resume_token_hash=f"resume-{uuid4()}",
        status="consented",
        last_step="questions",
        client_meta={},
    )
    db_session.add(session)
    db_session.flush()
    db_session.add(
        Answer(
            event_id=event.id,
            session_id=session.id,
            question_id=stale.id,
            answer_value=1,
            score_value=Decimal("1"),
        )
    )
    db_session.commit()

    try:
        seed_questions_for_event(db_session, event.slug)
    except SeedValidationError as exc:
        assert "stale question_no" in str(exc)
        assert "기존 테스트 응답 데이터가 있어 자동 삭제하지 않음" in str(exc)
    else:
        raise AssertionError("Expected stale question with answers to block seed.")
