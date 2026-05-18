from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.answer import Answer
from app.models.question import Question
from app.repositories.events import EventRepository
from app.repositories.questions import QuestionRepository
from app.services.scoring import RULE_VERSION

QUESTIONS_FILENAME = "questions_fire_expo_2026_final_260518.json"
SCORING_RULES_FILENAME = "scoring_rules_v4_final_260518.json"
EXPECTED_QUESTION_COUNT = 64
EXPECTED_QUESTION_NOS = set(range(1, 65))
ALLOWED_SCALE_CODES = {"profile", "kmies", "phq9", "pcl5", "kscs"}


class SeedValidationError(ValueError):
    pass


def _candidate_seed_paths(filename: str) -> list[Path]:
    script_path = Path(__file__).resolve()
    api_root = script_path.parents[2]
    repo_root = script_path.parents[3]

    return [
        script_path.parents[1] / "seeds" / "data" / filename,
        repo_root / "docs" / "data" / filename,
        api_root / "docs" / "data" / filename,
        Path.cwd() / "docs" / "data" / filename,
        Path.cwd().parent / "docs" / "data" / filename,
    ]


def find_seed_file(filename: str) -> Path:
    for path in _candidate_seed_paths(filename):
        if path.exists():
            return path
    searched = ", ".join(str(path) for path in _candidate_seed_paths(filename))
    raise FileNotFoundError(f"{filename} seed file was not found. searched={searched}")


def _read_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8-sig")
    if chr(0xFFFD) in raw:
        raise SeedValidationError(f"{path} contains Unicode replacement characters.")
    return json.loads(raw)


def load_questions_seed(path: Path | None = None) -> dict[str, Any]:
    seed_path = path or find_seed_file(QUESTIONS_FILENAME)
    data = _read_json(seed_path)
    validate_questions_seed(data)
    return data


def load_scoring_rules_seed(path: Path | None = None) -> dict[str, Any]:
    seed_path = path or find_seed_file(SCORING_RULES_FILENAME)
    data = _read_json(seed_path)
    if data.get("ruleVersion") != RULE_VERSION:
        raise SeedValidationError(
            f"Unexpected scoring rule version: {data.get('ruleVersion')}"
        )
    return data


def validate_questions_seed(data: dict[str, Any]) -> None:
    metadata = data.get("metadata", {})
    questions = data.get("questions", [])

    if metadata.get("encoding", "").lower() != "utf-8":
        raise SeedValidationError("questions seed metadata.encoding must be utf-8.")
    if metadata.get("questionCount") != EXPECTED_QUESTION_COUNT:
        raise SeedValidationError(
            f"questions seed metadata.questionCount must be {EXPECTED_QUESTION_COUNT}."
        )
    if metadata.get("ruleVersion") != RULE_VERSION:
        raise SeedValidationError(
            f"questions seed ruleVersion must be {RULE_VERSION}."
        )
    if len(questions) != EXPECTED_QUESTION_COUNT:
        raise SeedValidationError(
            f"questions seed questions array must contain {EXPECTED_QUESTION_COUNT} items."
        )

    question_nos = {question.get("questionNo") for question in questions}
    if question_nos != EXPECTED_QUESTION_NOS:
        raise SeedValidationError(
            f"questions seed must contain questionNo 1 through {EXPECTED_QUESTION_COUNT}."
        )

    question_keys = [question.get("questionKey") for question in questions]
    if len(set(question_keys)) != len(question_keys):
        raise SeedValidationError("questions seed questionKey values must be unique.")

    display_orders = [question.get("displayOrder") for question in questions]
    if set(display_orders) != EXPECTED_QUESTION_NOS:
        raise SeedValidationError(
            f"questions seed displayOrder values must contain 1 through {EXPECTED_QUESTION_COUNT}."
        )

    scale_codes = {question.get("scaleCode") for question in questions}
    unsupported_scale_codes = sorted(scale_codes - ALLOWED_SCALE_CODES)
    if unsupported_scale_codes:
        raise SeedValidationError(
            f"questions seed contains unsupported scaleCode values: {unsupported_scale_codes}"
        )


def _answer_counts_by_question_id(
    db: Session,
    question_ids,
) -> dict:
    question_ids = list(question_ids)
    if not question_ids:
        return {}

    rows = db.execute(
        select(Answer.question_id, func.count(Answer.id))
        .where(Answer.question_id.in_(question_ids))
        .group_by(Answer.question_id)
    ).all()
    return {question_id: int(count or 0) for question_id, count in rows}


def _prepare_existing_questions_for_final_seed(
    db: Session,
    *,
    event_id,
    final_questions: list[dict[str, Any]],
) -> int:
    existing_questions = list(
        db.execute(select(Question).where(Question.event_id == event_id)).scalars()
    )
    if not existing_questions:
        return 0

    final_by_no = {question["questionNo"]: question for question in final_questions}
    answer_counts = _answer_counts_by_question_id(
        db,
        [question.id for question in existing_questions],
    )
    blocked_question_nos: list[int] = []

    for question in existing_questions:
        final_question = final_by_no.get(question.question_no)
        is_stale = final_question is None
        is_conflicting = final_question is not None and (
            question.question_key != final_question["questionKey"]
            or question.scale_code != final_question["scaleCode"]
            or question.question_type != final_question["questionType"]
        )
        if (is_stale or is_conflicting) and answer_counts.get(question.id, 0) > 0:
            blocked_question_nos.append(question.question_no)

    if blocked_question_nos:
        raise SeedValidationError(
            "stale/conflicting question_no "
            f"{sorted(blocked_question_nos)} have existing answers; "
            "refusing automatic deletion."
        )

    deleted_stale = 0
    for question in existing_questions:
        if question.question_no not in final_by_no:
            db.delete(question)
            deleted_stale += 1
            continue

        final_question = final_by_no[question.question_no]
        if question.question_key != final_question["questionKey"]:
            question.question_key = f"__seed_rekey__{question.id.hex}"
            db.add(question)

    db.flush()
    return deleted_stale


def seed_questions_for_event(
    db: Session,
    event_slug: str,
    questions_seed: dict[str, Any] | None = None,
) -> dict[str, int]:
    load_scoring_rules_seed()
    data = questions_seed or load_questions_seed()
    event = EventRepository(db).get_by_slug(event_slug)
    if event is None:
        raise SeedValidationError(f"Event not found for slug: {event_slug}")

    repository = QuestionRepository(db)
    created = 0
    updated = 0
    deleted_stale = _prepare_existing_questions_for_final_seed(
        db,
        event_id=event.id,
        final_questions=data["questions"],
    )

    for item in data["questions"]:
        _question, was_created = repository.upsert_question(
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
        if was_created:
            created += 1
        else:
            updated += 1

    db.commit()
    return {
        "created": created,
        "updated": updated,
        "deletedStale": deleted_stale,
        "total": created + updated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed event questions from JSON.")
    parser.add_argument("--event-slug", default="fire-expo-2026")
    args = parser.parse_args()

    try:
        with Session(bind=get_engine()) as db:
            result = seed_questions_for_event(db, args.event_slug)
    except (FileNotFoundError, SeedValidationError) as exc:
        print(f"questions_seed_failed {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print(
        "questions_seeded "
        f"event_slug={args.event_slug} "
        f"created={result['created']} "
        f"updated={result['updated']} "
        f"deleted_stale={result['deletedStale']} "
        f"total={result['total']}"
    )


if __name__ == "__main__":
    main()
