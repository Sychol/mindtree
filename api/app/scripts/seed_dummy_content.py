from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models.card import MindCard
from app.models.enums import (
    ContentOrigin,
    KeywordCategory,
    KeywordExtractionMethod,
    KeywordSourceType,
    KeywordStatus,
    PublicStatus,
    ReplyType,
    SafetyStatus,
)
from app.models.event import Event
from app.models.keyword import Keyword
from app.models.reply import Reply
from app.services.keyword_job_factory import create_keyword_job_for_card, create_keyword_job_for_reply

DEFAULT_EVENT_SLUG = "fire-expo-2026"
DEFAULT_CARDS = 100
DEFAULT_REPLIES = 100
DEFAULT_KEYWORDS = 100
DEFAULT_BATCH_LABEL = "dummy-content-v1"
VALID_MODES = {"missing", "force"}

CARD_BASES = [
    "현장에 다녀온 뒤에도 긴장이 쉽게 풀리지 않았습니다.",
    "몸은 쉬고 있는데 마음은 아직 현장에 남아 있는 것 같습니다.",
    "반복해서 떠오르는 장면 때문에 잠들기가 어려웠습니다.",
    "작은 소리에도 몸이 먼저 긴장하는 날이 있었습니다.",
    "동료와 짧게 나눈 말이 그날을 지나가게 해 주었습니다.",
    "잘 해내고 싶다는 마음이 오히려 부담으로 남았습니다.",
    "쉬어도 되는지 스스로에게 허락하기 어려웠습니다.",
    "괜찮다고 말했지만 마음 한편은 계속 무거웠습니다.",
    "오늘은 조금 천천히 숨을 고르고 싶었습니다.",
    "내가 할 수 있었던 것과 없었던 것을 구분해 보려 합니다.",
]

CARD_VARIANTS = [
    "그래도 지금은 안전한 곳에 있다는 사실을 떠올려 봅니다.",
    "오늘 하루는 조금 낮은 속도로 지나가도 된다고 생각합니다.",
    "마음이 서두르지 않도록 짧게 쉬어 가려 합니다.",
    "혼자 판단하기보다 믿을 만한 사람과 나누고 싶습니다.",
    "작은 회복의 신호를 놓치지 않으려 합니다.",
    "몸의 긴장을 알아차리고 천천히 풀어 보려 합니다.",
    "그때의 나를 탓하기보다 애쓴 마음을 인정해 봅니다.",
    "지금 할 수 있는 한 가지에만 집중해 보려 합니다.",
    "잠깐 멈추고 물을 마시며 숨을 고르고 싶습니다.",
    "완벽히 괜찮지 않아도 괜찮다고 말해 주고 싶습니다.",
]

REPLY_BASES = [
    "그 시간을 견뎌낸 것만으로도 충분히 애쓰셨습니다.",
    "오늘은 잠시 쉬어가도 괜찮습니다.",
    "혼자 감당하지 않아도 됩니다. 곁에 기대어도 괜찮습니다.",
    "천천히 숨을 고르며 지금의 나를 돌봐 주세요.",
    "작은 회복의 걸음 하나만으로도 충분합니다.",
    "말로 꺼낸 용기가 이미 큰 시작입니다.",
    "잠깐 물을 마시고 어깨의 힘을 풀어 보세요.",
    "당신의 마음이 조금은 편안해지기를 응원합니다.",
    "완벽하지 않아도 괜찮습니다. 오늘도 충분히 해냈습니다.",
    "필요할 때 도움을 청하는 것도 회복의 한 방법입니다.",
]

REPLY_VARIANTS = [
    "지금은 안전한 곳에서 천천히 돌아와도 됩니다.",
    "마음이 따라오는 데 시간이 걸릴 수 있습니다.",
    "오늘의 작은 쉼이 내일의 힘이 되기를 바랍니다.",
    "같은 마음으로 곁에서 응원하겠습니다.",
    "숨을 한 번 고르는 순간도 충분한 돌봄입니다.",
    "당신이 지나온 시간을 가볍게 여기지 않겠습니다.",
    "힘든 마음을 알아차린 것부터 회복의 시작입니다.",
    "서두르지 않아도 괜찮습니다.",
    "잠깐 멈추는 선택도 용기입니다.",
    "필요한 만큼 쉬어 갈 수 있기를 바랍니다.",
]

KEYWORD_POOLS = {
    KeywordCategory.MIND_SIGNAL.value: [
        "긴장",
        "피로",
        "답답함",
        "불면",
        "막막함",
        "부담감",
        "죄책감",
        "놀람",
        "무기력",
        "반복생각",
        "예민함",
        "두근거림",
        "마음무거움",
        "걱정",
        "지침",
    ],
    KeywordCategory.SUPPORT.value: [
        "응원",
        "위로",
        "공감",
        "함께",
        "감사",
        "괜찮아",
        "다정함",
        "동료",
        "지지",
        "용기",
    ],
    KeywordCategory.RECOVERY.value: [
        "쉼",
        "회복",
        "안정",
        "휴식",
        "숨고르기",
        "편안함",
        "여유",
        "따뜻함",
        "회복력",
        "마음돌봄",
    ],
    KeywordCategory.COPING.value: [
        "호흡",
        "산책",
        "물마시기",
        "대화",
        "상담",
        "기록하기",
        "스트레칭",
        "잠시멈춤",
        "천천히",
        "도움요청",
    ],
}

KEYWORD_WEIGHTS = [
    Decimal("24"),
    Decimal("19"),
    Decimal("16"),
    Decimal("13"),
    Decimal("11"),
    Decimal("9"),
    Decimal("8"),
    Decimal("7"),
    Decimal("6"),
    Decimal("5"),
    Decimal("4"),
    Decimal("3"),
    Decimal("21"),
    Decimal("15"),
    Decimal("12"),
    Decimal("10"),
    Decimal("18"),
    Decimal("14"),
    Decimal("6"),
    Decimal("4"),
]


@dataclass(frozen=True)
class SeedDummyContentResult:
    event_slug: str
    batch_label: str
    cards_requested: int
    cards_created: int
    cards_skipped_existing: int
    replies_requested: int
    replies_created: int
    replies_skipped_existing: int
    keywords_requested: int
    keywords_created: int
    keywords_updated: int
    keywords_skipped_existing: int
    force_excluded_cards: int
    force_excluded_replies: int
    force_excluded_keywords: int


@dataclass(frozen=True)
class _KeywordSeed:
    keyword_text: str
    normalized_keyword: str
    category: str
    weight: Decimal


def _prompt_type(index: int) -> str:
    slot = index % 20
    if slot < 14:
        return "stress_memory"
    if slot < 17:
        return "to_now_me"
    if slot < 19:
        return "to_past_me"
    return "to_colleague"


def _card_content(index: int) -> str:
    base = CARD_BASES[index % len(CARD_BASES)]
    variant = CARD_VARIANTS[(index // len(CARD_BASES)) % len(CARD_VARIANTS)]
    return f"{base} {variant}"


def _reply_content(index: int) -> str:
    base = REPLY_BASES[index % len(REPLY_BASES)]
    variant = REPLY_VARIANTS[(index // len(REPLY_BASES)) % len(REPLY_VARIANTS)]
    return f"{base} {variant}"


def _reply_type(index: int) -> str:
    reply_types = [
        ReplyType.COMFORT.value,
        ReplyType.EMPATHY.value,
        ReplyType.SMALL_COPING.value,
    ]
    return reply_types[index % len(reply_types)]


def _category_counts(total: int) -> list[tuple[str, int]]:
    if total <= 0:
        return []

    ratios = [
        (KeywordCategory.MIND_SIGNAL.value, Decimal("0.35")),
        (KeywordCategory.SUPPORT.value, Decimal("0.25")),
        (KeywordCategory.RECOVERY.value, Decimal("0.25")),
        (KeywordCategory.COPING.value, Decimal("0.15")),
    ]
    counts = [(category, int(total * ratio)) for category, ratio in ratios]
    assigned = sum(count for _, count in counts)
    index = 0
    while assigned < total:
        category, count = counts[index % len(counts)]
        counts[index % len(counts)] = (category, count + 1)
        assigned += 1
        index += 1
    return counts


def _keyword_seeds(total: int) -> list[_KeywordSeed]:
    seeds: list[_KeywordSeed] = []
    global_index = 0
    for category, count in _category_counts(total):
        pool = KEYWORD_POOLS[category]
        for category_index in range(count):
            normalized = pool[category_index % len(pool)]
            seeds.append(
                _KeywordSeed(
                    keyword_text=f"{normalized} seed {global_index + 1:03d}",
                    normalized_keyword=normalized,
                    category=category,
                    weight=KEYWORD_WEIGHTS[global_index % len(KEYWORD_WEIGHTS)],
                )
            )
            global_index += 1
    return seeds


def _get_event(db: Session, event_slug: str) -> Event:
    event = db.execute(select(Event).where(Event.slug == event_slug)).scalar_one_or_none()
    if event is None:
        raise RuntimeError("Event not found. Run seed_dev first or create event.")
    return event


def _force_exclude_cards(db: Session, event_id, batch_label: str) -> int:
    cards = list(
        db.execute(
            select(MindCard).where(
                MindCard.event_id == event_id,
                MindCard.origin == ContentOrigin.SYSTEM_SEED.value,
                MindCard.origin_tag == batch_label,
            )
        ).scalars()
    )
    changed = 0
    for card in cards:
        if card.public_status != PublicStatus.EXCLUDED.value or card.safety_status != SafetyStatus.EXCLUDE.value:
            changed += 1
        card.public_status = PublicStatus.EXCLUDED.value
        card.safety_status = SafetyStatus.EXCLUDE.value
        db.add(card)
    db.flush()
    return changed


def _force_exclude_replies(db: Session, event_id, batch_label: str) -> int:
    replies = list(
        db.execute(
            select(Reply).where(
                Reply.event_id == event_id,
                Reply.origin == ContentOrigin.SYSTEM_SEED.value,
                Reply.origin_tag == batch_label,
            )
        ).scalars()
    )
    changed = 0
    for reply in replies:
        if reply.public_status != PublicStatus.EXCLUDED.value or reply.safety_status != SafetyStatus.EXCLUDE.value:
            changed += 1
        reply.public_status = PublicStatus.EXCLUDED.value
        reply.safety_status = SafetyStatus.EXCLUDE.value
        db.add(reply)
    db.flush()
    return changed


def _force_exclude_keywords(db: Session, event_id, batch_label: str) -> int:
    keywords = list(
        db.execute(
            select(Keyword).where(
                Keyword.event_id == event_id,
                Keyword.origin == ContentOrigin.SYSTEM_SEED.value,
                Keyword.origin_tag == batch_label,
            )
        ).scalars()
    )
    changed = 0
    for keyword in keywords:
        if keyword.status != KeywordStatus.EXCLUDED.value:
            changed += 1
        keyword.status = KeywordStatus.EXCLUDED.value
        db.add(keyword)
    db.flush()
    return changed


def _find_card(db: Session, event_id, batch_label: str, content: str) -> MindCard | None:
    return db.execute(
        select(MindCard)
        .where(
            MindCard.event_id == event_id,
            MindCard.origin == ContentOrigin.SYSTEM_SEED.value,
            MindCard.origin_tag == batch_label,
            MindCard.content_raw == content,
        )
        .order_by(MindCard.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _find_reply(db: Session, event_id, batch_label: str, content: str) -> Reply | None:
    return db.execute(
        select(Reply)
        .where(
            Reply.event_id == event_id,
            Reply.origin == ContentOrigin.SYSTEM_SEED.value,
            Reply.origin_tag == batch_label,
            Reply.content_raw == content,
        )
        .order_by(Reply.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _find_keyword(db: Session, event_id, batch_label: str, seed: _KeywordSeed) -> Keyword | None:
    return db.execute(
        select(Keyword)
        .where(
            Keyword.event_id == event_id,
            Keyword.origin == ContentOrigin.SYSTEM_SEED.value,
            Keyword.origin_tag == batch_label,
            Keyword.source_type == KeywordSourceType.ADMIN_MANUAL.value,
            Keyword.source_id.is_(None),
            Keyword.keyword_text == seed.keyword_text,
            Keyword.normalized_keyword == seed.normalized_keyword,
            Keyword.category == seed.category,
        )
        .order_by(Keyword.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def _seed_cards(
    db: Session,
    event: Event,
    *,
    count: int,
    batch_label: str,
    ignore_existing: bool,
    create_keyword_jobs: bool,
) -> tuple[int, int]:
    created = 0
    skipped_existing = 0
    now = datetime.now(timezone.utc)
    for index in range(count):
        content = _card_content(index)
        existing = None if ignore_existing else _find_card(db, event.id, batch_label, content)
        if existing is not None:
            existing.safety_status = SafetyStatus.SAFE.value
            existing.public_status = PublicStatus.PUBLIC.value
            existing.reviewed_at = now
            db.add(existing)
            skipped_existing += 1
            continue

        card = MindCard(
            event_id=event.id,
            session_id=None,
            prompt_type=_prompt_type(index),
            content_raw=content,
            content_redacted=None,
            safety_status=SafetyStatus.SAFE.value,
            public_status=PublicStatus.PUBLIC.value,
            moderation_reason=None,
            origin=ContentOrigin.SYSTEM_SEED.value,
            origin_tag=batch_label,
            created_by_admin_id=None,
            reviewed_at=now,
            reviewed_by=None,
        )
        db.add(card)
        db.flush()
        if create_keyword_jobs:
            create_keyword_job_for_card(db, card)
        created += 1
    return created, skipped_existing


def _seed_replies(
    db: Session,
    event: Event,
    *,
    count: int,
    batch_label: str,
    ignore_existing: bool,
    create_keyword_jobs: bool,
) -> tuple[int, int]:
    created = 0
    skipped_existing = 0
    now = datetime.now(timezone.utc)
    for index in range(count):
        content = _reply_content(index)
        existing = None if ignore_existing else _find_reply(db, event.id, batch_label, content)
        if existing is not None:
            existing.safety_status = SafetyStatus.SAFE.value
            existing.public_status = PublicStatus.PUBLIC.value
            existing.reviewed_at = now
            db.add(existing)
            skipped_existing += 1
            continue

        reply = Reply(
            event_id=event.id,
            session_id=None,
            target_card_id=None,
            reply_type=_reply_type(index),
            content_raw=content,
            content_redacted=None,
            safety_status=SafetyStatus.SAFE.value,
            public_status=PublicStatus.PUBLIC.value,
            moderation_reason=None,
            origin=ContentOrigin.SYSTEM_SEED.value,
            origin_tag=batch_label,
            created_by_admin_id=None,
            reviewed_at=now,
            reviewed_by=None,
        )
        db.add(reply)
        db.flush()
        if create_keyword_jobs:
            create_keyword_job_for_reply(db, reply)
        created += 1
    return created, skipped_existing


def _seed_keywords(
    db: Session,
    event: Event,
    *,
    count: int,
    batch_label: str,
    ignore_existing: bool,
) -> tuple[int, int, int]:
    created = 0
    updated = 0
    skipped_existing = 0
    for seed in _keyword_seeds(count):
        existing = None if ignore_existing else _find_keyword(db, event.id, batch_label, seed)
        if existing is not None:
            changed = (
                existing.status != KeywordStatus.ACTIVE.value
                or existing.weight != seed.weight
                or existing.keyword_text != seed.keyword_text
            )
            existing.status = KeywordStatus.ACTIVE.value
            existing.weight = seed.weight
            existing.keyword_text = seed.keyword_text
            existing.extraction_method = KeywordExtractionMethod.ADMIN.value
            db.add(existing)
            if changed:
                updated += 1
            else:
                skipped_existing += 1
            continue

        db.add(
            Keyword(
                event_id=event.id,
                source_type=KeywordSourceType.ADMIN_MANUAL.value,
                source_id=None,
                keyword_text=seed.keyword_text,
                normalized_keyword=seed.normalized_keyword,
                category=seed.category,
                weight=seed.weight,
                status=KeywordStatus.ACTIVE.value,
                extraction_method=KeywordExtractionMethod.ADMIN.value,
                job_id=None,
                origin=ContentOrigin.SYSTEM_SEED.value,
                origin_tag=batch_label,
                created_by_admin_id=None,
            )
        )
        created += 1
    db.flush()
    return created, updated, skipped_existing


def _count_existing(db: Session, model, event_id, batch_label: str) -> int:
    return int(
        db.execute(
            select(func.count(model.id)).where(
                model.event_id == event_id,
                model.origin == ContentOrigin.SYSTEM_SEED.value,
                model.origin_tag == batch_label,
            )
        ).scalar_one()
        or 0
    )


def seed_dummy_content(
    db: Session,
    *,
    event_slug: str,
    cards: int,
    replies: int,
    keywords: int,
    batch_label: str,
    mode: str,
    create_keyword_jobs: bool = False,
) -> SeedDummyContentResult:
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of: {', '.join(sorted(VALID_MODES))}")
    if cards < 0 or replies < 0 or keywords < 0:
        raise ValueError("cards, replies, and keywords must be non-negative")

    event = _get_event(db, event_slug)
    force_excluded_cards = 0
    force_excluded_replies = 0
    force_excluded_keywords = 0
    ignore_existing = mode == "force"

    if mode == "force":
        force_excluded_cards = _force_exclude_cards(db, event.id, batch_label)
        force_excluded_replies = _force_exclude_replies(db, event.id, batch_label)
        force_excluded_keywords = _force_exclude_keywords(db, event.id, batch_label)

    cards_created = cards_skipped_existing = 0
    replies_created = replies_skipped_existing = 0
    keywords_created = keywords_updated = keywords_skipped_existing = 0

    if mode == "missing" and _count_existing(db, MindCard, event.id, batch_label) >= cards:
        cards_skipped_existing = cards
    else:
        cards_created, cards_skipped_existing = _seed_cards(
            db,
            event,
            count=cards,
            batch_label=batch_label,
            ignore_existing=ignore_existing,
            create_keyword_jobs=create_keyword_jobs,
        )

    if mode == "missing" and _count_existing(db, Reply, event.id, batch_label) >= replies:
        replies_skipped_existing = replies
    else:
        replies_created, replies_skipped_existing = _seed_replies(
            db,
            event,
            count=replies,
            batch_label=batch_label,
            ignore_existing=ignore_existing,
            create_keyword_jobs=create_keyword_jobs,
        )

    if mode == "missing" and _count_existing(db, Keyword, event.id, batch_label) >= keywords:
        keywords_skipped_existing = keywords
    else:
        keywords_created, keywords_updated, keywords_skipped_existing = _seed_keywords(
            db,
            event,
            count=keywords,
            batch_label=batch_label,
            ignore_existing=ignore_existing,
        )

    db.commit()
    return SeedDummyContentResult(
        event_slug=event.slug,
        batch_label=batch_label,
        cards_requested=cards,
        cards_created=cards_created,
        cards_skipped_existing=cards_skipped_existing,
        replies_requested=replies,
        replies_created=replies_created,
        replies_skipped_existing=replies_skipped_existing,
        keywords_requested=keywords,
        keywords_created=keywords_created,
        keywords_updated=keywords_updated,
        keywords_skipped_existing=keywords_skipped_existing,
        force_excluded_cards=force_excluded_cards,
        force_excluded_replies=force_excluded_replies,
        force_excluded_keywords=force_excluded_keywords,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed cold-start system content without participant sessions, survey answers, or completion codes."
    )
    parser.add_argument("--event-slug", default=DEFAULT_EVENT_SLUG)
    parser.add_argument("--cards", type=int, default=DEFAULT_CARDS)
    parser.add_argument("--replies", type=int, default=DEFAULT_REPLIES)
    parser.add_argument("--keywords", type=int, default=DEFAULT_KEYWORDS)
    parser.add_argument("--batch-label", default=DEFAULT_BATCH_LABEL)
    parser.add_argument("--mode", choices=sorted(VALID_MODES), default="missing")
    parser.add_argument("--create-keyword-jobs", action="store_true")
    args = parser.parse_args()

    with Session(bind=get_engine()) as db:
        result = seed_dummy_content(
            db,
            event_slug=args.event_slug,
            cards=args.cards,
            replies=args.replies,
            keywords=args.keywords,
            batch_label=args.batch_label,
            mode=args.mode,
            create_keyword_jobs=args.create_keyword_jobs,
        )

    print(
        "dummy_content_seeded "
        f"event_slug={result.event_slug} "
        f"batch_label={result.batch_label} "
        f"cards_requested={result.cards_requested} "
        f"cards_created={result.cards_created} "
        f"cards_skipped_existing={result.cards_skipped_existing} "
        f"replies_requested={result.replies_requested} "
        f"replies_created={result.replies_created} "
        f"replies_skipped_existing={result.replies_skipped_existing} "
        f"keywords_requested={result.keywords_requested} "
        f"keywords_created={result.keywords_created} "
        f"keywords_updated={result.keywords_updated} "
        f"keywords_skipped_existing={result.keywords_skipped_existing} "
        f"force_excluded_cards={result.force_excluded_cards} "
        f"force_excluded_replies={result.force_excluded_replies} "
        f"force_excluded_keywords={result.force_excluded_keywords}"
    )


if __name__ == "__main__":
    main()
