from enum import StrEnum


class EventStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    ARCHIVED = "archived"


class SessionStatus(StrEnum):
    CREATED = "created"
    CONSENTED = "consented"
    QUESTIONS_COMPLETED = "questions_completed"
    SUMMARY_VIEWED = "summary_viewed"
    CARD_CREATED = "card_created"
    REPLY_CREATED = "reply_created"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class QuestionType(StrEnum):
    SINGLE_SELECT = "single_select"
    MULTI_SELECT = "multi_select"
    LIKERT = "likert"
    TEXT = "text"
    NUMBER = "number"


class ScaleCode(StrEnum):
    PROFILE = "profile"
    PHQ9 = "phq9"
    PCL5 = "pcl5"
    KMIES = "kmies"
    KSCS = "kscs"


class SafetyStatus(StrEnum):
    SAFE = "safe"
    REVIEW = "review"
    EXCLUDE = "exclude"


class PublicStatus(StrEnum):
    PENDING = "pending"
    PUBLIC = "public"
    HIDDEN = "hidden"
    EXCLUDED = "excluded"


class ReplyType(StrEnum):
    COMFORT = "comfort"
    EMPATHY = "empathy"
    SMALL_COPING = "small_coping"


class KeywordJobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRY_WAIT = "retry_wait"


class KeywordSourceType(StrEnum):
    MIND_CARD = "mind_card"
    REPLY = "reply"
    SUMMARY = "summary"


class KeywordCategory(StrEnum):
    MIND_SIGNAL = "mind_signal"
    SUPPORT = "support"
    RECOVERY = "recovery"
    COPING = "coping"
    NEUTRAL = "neutral"


class KeywordStatus(StrEnum):
    ACTIVE = "active"
    HIDDEN = "hidden"
    EXCLUDED = "excluded"


class KeywordExtractionMethod(StrEnum):
    LLM = "llm"
    FALLBACK = "fallback"
    ADMIN = "admin"


class CompletionCodeStatus(StrEnum):
    ISSUED = "issued"
    REDEEMED = "redeemed"
    VOID = "void"
