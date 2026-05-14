from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.repositories.events import EventRepository
from app.repositories.questions import QuestionRepository
from app.services.scoring import RULE_VERSION

QUESTIONS_FILENAME = "questions_fire_expo_2026.json"
SCORING_RULES_FILENAME = "scoring_rules_v1.json"
EXPECTED_QUESTION_COUNT = 77
EXPECTED_QUESTION_NOS = set(range(1, 78))


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
    if "�" in raw:
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
        raise SeedValidationError("questions seed metadata.questionCount must be 77.")
    if metadata.get("ruleVersion") != RULE_VERSION:
        raise SeedValidationError(
            f"questions seed ruleVersion must be {RULE_VERSION}."
        )
    if len(questions) != EXPECTED_QUESTION_COUNT:
        raise SeedValidationError("questions seed questions array must contain 77 items.")

    question_nos = {question.get("questionNo") for question in questions}
    if question_nos != EXPECTED_QUESTION_NOS:
        raise SeedValidationError("questions seed must contain questionNo 1 through 77.")


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
        f"total={result['total']}"
    )


if __name__ == "__main__":
    main()
