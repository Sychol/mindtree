from __future__ import annotations

import argparse
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.card import MindCard
from app.models.completion import CompletionCode
from app.models.event import Event
from app.models.question import Question
from app.models.session import Session as EventSession
from app.schemas.answers import AnswerInput, BulkAnswerRequest
from app.schemas.cards import CreateMindCardRequest, SelectCardRequest
from app.schemas.replies import CreateReplyRequest
from app.schemas.sessions import ConsentRequest
from app.scripts.seed_dev import EVENT_SLUG, seed_dev
from app.services.answers import save_bulk_answers
from app.services.cards import create_mind_card, list_public_cards, select_peer_card
from app.services.consent import accept_consent
from app.services.replies import create_reply
from app.services.summaries import mark_summary_viewed

DEFAULT_COUNT = 30
DEFAULT_BATCH_LABEL = "dummy-participants-v1"

CARD_CONTENTS = [
    "오늘은 잠깐 멈추고 숨을 고르며 다시 시작해 보려 합니다.",
    "마음이 무거웠지만 동료와 나눈 짧은 말이 큰 힘이 되었습니다.",
    "완벽하지 않아도 괜찮다는 말을 스스로에게 건네고 싶습니다.",
    "힘든 장면이 떠오를 때 차분히 호흡하며 지금 할 수 있는 일을 떠올립니다.",
    "혼자 버티기보다 주변에 기대어도 된다는 걸 조금씩 배우고 있습니다.",
    "작은 휴식과 따뜻한 말 한마디가 하루를 지나가게 해 주었습니다.",
    "마음이 흔들릴 때에도 내가 해낸 일들을 천천히 기억하려 합니다.",
    "오늘의 나에게 필요한 건 더 몰아붙이는 말보다 충분했다는 말입니다.",
    "긴장이 올라올 때 발을 바닥에 단단히 두고 현재로 돌아오려 합니다.",
    "서로의 고단함을 알아봐 주는 순간 마음이 조금 가벼워졌습니다.",
]

REPLY_CONTENTS = [
    "그 시간을 견뎌낸 것만으로도 충분히 애쓰셨습니다.",
    "당신의 마음이 조금은 편안해지기를 조용히 응원합니다.",
    "혼자 감당하지 않아도 됩니다. 곁에 기대어 쉬어도 괜찮습니다.",
    "오늘은 아주 작은 회복의 걸음 하나만으로도 충분합니다.",
    "그 마음을 말로 꺼낸 용기가 이미 큰 시작이라고 생각합니다.",
    "천천히 숨을 고르며 자신에게 조금 더 다정해지면 좋겠습니다.",
]

REPLY_TYPES = ["comfort", "empathy", "small_coping"]


@dataclass(frozen=True)
class SeedDummyResult:
    requested: int
    created: int
    skipped_existing: int
    cards_created: int
    replies_created: int
    completion_codes_created: int
    batch_label: str


def _participant_key(batch_label: str, index: int) -> str:
    return f"seed-{batch_label}-{index:02d}"


def _consent_payload(consent_version: str) -> ConsentRequest:
    return ConsentRequest(
        consent_version=consent_version,
        accepted_items={
            "researchParticipationConsent": True,
            "personalDataUseConsent": True,
            "sensitiveInfoConsent": True,
            "deidentifiedAiRagUseConsent": True,
        },
    )


def _profile_answer(question: Question, index: int):
    values = [option["value"] for option in question.options]
    if question.question_no == 1:
        return values[index % len(values)]
    if question.question_no == 2:
        return values[index % len(values)]
    if question.question_no == 3:
        return ["q03_opt01", "q03_opt02", "q03_opt03", "q03_opt04"][index % 4]
    if question.question_no in {8, 11, 12, 13}:
        return [1, 2, 3, 4, 5][index % 5]
    return values[index % len(values)]


def _scale_values(question_nos: list[int], pattern: list[int], question_no: int) -> int:
    return pattern[question_nos.index(question_no)]


def _answer_value(question: Question, index: int):
    profile = index % 5
    kmies_patterns = [
        [1, 1, 2, 1, 2, 1, 1, 1, 1],
        [2, 3, 2, 3, 3, 2, 2, 2, 2],
        [4, 4, 3, 4, 4, 3, 4, 3, 4],
        [5, 5, 4, 5, 5, 4, 5, 4, 5],
        [3, 2, 3, 2, 3, 2, 3, 2, 3],
    ]
    phq9_patterns = [
        [0, 0, 1, 0, 1, 0, 0, 0, 0],
        [1, 1, 1, 0, 1, 0, 1, 1, 0],
        [1, 2, 1, 1, 2, 1, 1, 1, 0],
        [2, 2, 2, 1, 2, 1, 2, 2, 0],
        [0, 1, 0, 0, 1, 0, 1, 0, 0],
    ]
    pcl5_patterns = [
        [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
        [2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1],
        [1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2],
    ]
    kscs_patterns = [
        [2, 4, 4, 2, 4, 4, 4, 2, 2, 4, 2, 2],
        [3, 4, 3, 3, 4, 3, 4, 3, 3, 4, 3, 3],
        [4, 3, 3, 4, 3, 3, 3, 4, 4, 3, 4, 4],
        [5, 2, 2, 5, 2, 2, 2, 5, 5, 2, 5, 5],
        [2, 5, 4, 2, 5, 4, 4, 2, 2, 5, 2, 2],
    ]

    if question.scale_code == "profile":
        return _profile_answer(question, index)
    if question.scale_code == "kmies":
        return _scale_values(list(range(15, 24)), kmies_patterns[profile], question.question_no)
    if question.scale_code == "phq9":
        return _scale_values(list(range(24, 33)), phq9_patterns[profile], question.question_no)
    if question.scale_code == "pcl5":
        return _scale_values(list(range(33, 53)), pcl5_patterns[profile], question.question_no)
    if question.scale_code == "kscs":
        return _scale_values(list(range(53, 65)), kscs_patterns[profile], question.question_no)

    if question.question_type == "multi_select":
        return [question.options[0]["value"]]
    if question.options:
        return question.options[0]["value"]
    if question.question_type == "number":
        return 1
    return "더미 참가자 응답입니다."


def _build_answers(questions: list[Question], index: int) -> BulkAnswerRequest:
    return BulkAnswerRequest(
        answers=[
            AnswerInput(question_id=question.id, answer_value=_answer_value(question, index))
            for question in questions
        ],
        client_progress={"lastQuestionNo": questions[-1].question_no},
    )


def _existing_session(db: Session, event_id: UUID, key: str) -> EventSession | None:
    return db.execute(
        select(EventSession).where(
            EventSession.event_id == event_id,
            EventSession.anonymous_key_hash == key,
        )
    ).scalar_one_or_none()


def _create_session(db: Session, event: Event, key: str, index: int, batch_label: str) -> EventSession:
    session = EventSession(
        event_id=event.id,
        anonymous_key_hash=key,
        resume_token_hash=f"{key}-resume",
        status="created",
        last_step="landing",
        client_meta={
            "seed": "dummy_participants",
            "batch": batch_label,
            "participantNo": str(index),
        },
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _select_peer_card(db: Session, event_slug: str, session_id: UUID) -> UUID:
    public_cards = list_public_cards(
        db,
        event_slug=event_slug,
        exclude_session_id=session_id,
        limit=30,
    )
    if not public_cards.cards:
        raise RuntimeError("No public peer cards are available for dummy participant selection.")
    return public_cards.cards[0].id


def seed_dummy_participants(
    db: Session,
    *,
    count: int,
    event_slug: str,
    batch_label: str,
) -> SeedDummyResult:
    seed_dev(db)
    event = db.execute(select(Event).where(Event.slug == event_slug)).scalar_one()
    questions = list(
        db.execute(
            select(Question)
            .where(Question.event_id == event.id)
            .order_by(Question.display_order, Question.question_no)
        ).scalars()
    )
    if not questions:
        raise RuntimeError(f"No questions found for event_slug={event_slug}")

    created = 0
    skipped_existing = 0
    cards_created = 0
    replies_created = 0
    completion_codes_created = 0

    for index in range(1, count + 1):
        key = _participant_key(batch_label, index)
        if _existing_session(db, event.id, key) is not None:
            skipped_existing += 1
            continue

        session = _create_session(db, event, key, index, batch_label)
        accept_consent(
            db,
            session.id,
            _consent_payload(event.consent_version),
            ip_address=None,
            user_agent="seed_dummy_participants",
        )

        answers = save_bulk_answers(db, session.id, _build_answers(questions, index))
        if answers.missing_question_nos:
            raise RuntimeError(
                f"Dummy participant {index} has missing questions: {answers.missing_question_nos}"
            )

        mark_summary_viewed(db, session.id)
        create_mind_card(
            db,
            session.id,
            CreateMindCardRequest(
                prompt_type="stress_memory",
                content=CARD_CONTENTS[(index - 1) % len(CARD_CONTENTS)],
            ),
        )
        cards_created += 1

        selected_card_id = _select_peer_card(db, event_slug, session.id)
        select_peer_card(
            db,
            session.id,
            SelectCardRequest(selected_card_id=selected_card_id),
        )
        create_reply(
            db,
            session.id,
            CreateReplyRequest(
                target_card_id=selected_card_id,
                reply_type=REPLY_TYPES[(index - 1) % len(REPLY_TYPES)],
                content=REPLY_CONTENTS[(index - 1) % len(REPLY_CONTENTS)],
            ),
        )
        replies_created += 1

        completion_code = db.execute(
            select(CompletionCode).where(CompletionCode.session_id == session.id)
        ).scalar_one_or_none()
        if completion_code is None:
            raise RuntimeError(f"Completion code was not issued for dummy participant {index}.")
        completion_codes_created += 1
        created += 1

    return SeedDummyResult(
        requested=count,
        created=created,
        skipped_existing=skipped_existing,
        cards_created=cards_created,
        replies_created=replies_created,
        completion_codes_created=completion_codes_created,
        batch_label=batch_label,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed completed dummy participant flows.")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--event-slug", default=EVENT_SLUG)
    parser.add_argument("--batch-label", default=DEFAULT_BATCH_LABEL)
    args = parser.parse_args()

    with Session(bind=get_engine()) as db:
        result = seed_dummy_participants(
            db,
            count=args.count,
            event_slug=args.event_slug,
            batch_label=args.batch_label,
        )

    print(
        "dummy_participants_seeded "
        f"batch_label={result.batch_label} "
        f"requested={result.requested} "
        f"created={result.created} "
        f"skipped_existing={result.skipped_existing} "
        f"cards_created={result.cards_created} "
        f"replies_created={result.replies_created} "
        f"completion_codes_created={result.completion_codes_created}"
    )


if __name__ == "__main__":
    main()
