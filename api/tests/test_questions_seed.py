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
    path = ROOT / "docs" / "data" / "questions_fire_expo_2026_final_260518.json"

    raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)
    question_nos = [question["questionNo"] for question in data["questions"]]

    assert chr(0xFFFD) not in raw
    assert data["metadata"]["encoding"] == "utf-8"
    assert data["metadata"]["questionCount"] == 64
    assert data["metadata"]["ruleVersion"] == RULE_VERSION
    assert sorted(question_nos) == list(range(1, 65))

    scale_counts = {}
    for question in data["questions"]:
        scale_counts[question["scaleCode"]] = scale_counts.get(question["scaleCode"], 0) + 1
    assert scale_counts == {
        "profile": 14,
        "kmies": 9,
        "phq9": 9,
        "pcl5": 20,
        "kscs": 12,
    }
    by_no = {question["questionNo"]: question for question in data["questions"]}
    assert by_no[32]["questionKey"] == "phq9_09"
    assert by_no[32]["riskTrigger"]["type"] == "phq9_item9_positive"


def test_seed_questions_upserts_64_questions_without_duplicates(
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

    assert first == {"created": 64, "updated": 0, "deletedStale": 0, "total": 64}
    assert second == {"created": 0, "updated": 64, "deletedStale": 0, "total": 64}
    assert len(count) == 64


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

    assert result == {"created": 64, "updated": 0, "deletedStale": 1, "total": 64}
    assert [question.question_no for question in questions] == list(range(1, 65))


def test_seed_questions_upgrades_existing_v3_questions_without_answers(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    old_seed = json.loads(
        (ROOT / "docs" / "data" / "questions_fire_expo_2026_final_260515.json").read_text(
            encoding="utf-8-sig"
        )
    )
    for item in old_seed["questions"]:
        db_session.add(
            Question(
                event_id=event.id,
                question_no=item["questionNo"],
                scale_code=item["scaleCode"],
                question_key=item["questionKey"],
                title=item["title"],
                description=item.get("description"),
                question_type=item["questionType"],
                options=item.get("options", []),
                score_map=item.get("scoreMap", {}),
                required=bool(item.get("required", True)),
                display_order=item["displayOrder"],
            )
        )
    db_session.commit()

    result = seed_questions_for_event(db_session, event.slug)
    questions = db_session.execute(
        select(Question).where(Question.event_id == event.id).order_by(Question.question_no)
    ).scalars().all()

    assert result == {"created": 3, "updated": 61, "deletedStale": 0, "total": 64}
    assert [question.question_no for question in questions] == list(range(1, 65))
    assert questions[14].question_key == "kmies_01"
    assert questions[22].question_key == "kmies_09"
    assert questions[23].question_key == "phq9_01"
    assert questions[63].question_key == "kscs_12"


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
        assert "stale/conflicting question_no" in str(exc)
        assert "existing answers" in str(exc)
    else:
        raise AssertionError("Expected stale question with answers to block seed.")


def test_seed_questions_blocks_conflicting_questions_with_answers(
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    old_seed = json.loads(
        (ROOT / "docs" / "data" / "questions_fire_expo_2026_final_260515.json").read_text(
            encoding="utf-8-sig"
        )
    )
    old_question = next(question for question in old_seed["questions"] if question["questionNo"] == 21)
    question = Question(
        event_id=event.id,
        question_no=old_question["questionNo"],
        scale_code=old_question["scaleCode"],
        question_key=old_question["questionKey"],
        title=old_question["title"],
        description=old_question.get("description"),
        question_type=old_question["questionType"],
        options=old_question.get("options", []),
        score_map=old_question.get("scoreMap", {}),
        required=bool(old_question.get("required", True)),
        display_order=old_question["displayOrder"],
    )
    db_session.add(question)
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
            question_id=question.id,
            answer_value=0,
            score_value=Decimal("0"),
        )
    )
    db_session.commit()

    try:
        seed_questions_for_event(db_session, event.slug)
    except SeedValidationError as exc:
        message = str(exc)
        assert "stale/conflicting question_no" in message
        assert "21" in message
        assert "existing answers" in message
    else:
        raise AssertionError("Expected conflicting question with answers to block seed.")
