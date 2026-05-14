import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question import Question
from app.scripts.seed_questions import (
    RULE_VERSION,
    load_questions_seed,
    seed_questions_for_event,
)

ROOT = Path(__file__).resolve().parents[2]


def test_questions_seed_json_is_valid_utf8() -> None:
    path = ROOT / "docs" / "data" / "questions_fire_expo_2026.json"

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    question_nos = [question["questionNo"] for question in data["questions"]]

    assert data["metadata"]["encoding"] == "utf-8"
    assert data["metadata"]["questionCount"] == 77
    assert data["metadata"]["ruleVersion"] == RULE_VERSION
    assert sorted(question_nos) == list(range(1, 78))


def test_seed_questions_upserts_77_questions_without_duplicates(
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

    assert first == {"created": 77, "updated": 0, "total": 77}
    assert second == {"created": 0, "updated": 77, "total": 77}
    assert len(count) == 77
