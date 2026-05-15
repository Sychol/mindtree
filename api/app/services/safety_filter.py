from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.enums import PublicStatus, SafetyStatus


@dataclass(frozen=True)
class SafetyFilterResult:
    safety_status: str
    public_status: str
    moderation_reason: str | None
    content_redacted: str | None
    crisis_expression_detected: bool
    personal_info_detected: bool


PHONE_PATTERN = re.compile(r"(?<!\d)(?:01[016789]|02|0[3-6]\d)[-\s.]?\d{3,4}[-\s.]?\d{4}(?!\d)")
EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
AFFILIATION_PATTERN = re.compile(
    r"(?:제\s*이름|내\s*이름|저는\s*[가-힣]{2,4}\s*입니다|"
    r"[가-힣]{2,4}\s*(?:소방서|센터|본부|팀|회사|학교|병원|구급대|구조대)|"
    r"(?:소속|근무지|주소|사는\s*곳|현장명|사건명)\s*(?:은|는|:))"
)
SPECIFIC_EVENT_PATTERN = re.compile(
    r"\d{4}[년.-]\s*\d{1,2}[월.-]\s*\d{1,2}일?|"
    r"\d{1,2}월\s*\d{1,2}일|"
    r"(?:역|동|로|길|아파트|건물|상가|현장)\s*(?:에서|앞|근처)"
)
CRISIS_PATTERN = re.compile(
    r"(자살|자해|죽고\s*싶|죽어버리고\s*싶|목숨을\s*끊|극단적\s*선택|"
    r"뛰어내리|손목을\s*그|살기\s*싫|사라지고\s*싶)"
)
ABUSE_PATTERN = re.compile(
    r"(시발|씨발|병신|개새끼|좆|꺼져|죽어라|혐오|쓰레기|"
    r"[가-힣]{2,4}\s*(?:때문에|탓에)\s*(?:망했|죽었|다쳤))"
)
MEDICAL_ASSERTION_PATTERN = re.compile(
    r"(우울증입니다|PTSD입니다|외상후\s*스트레스|도덕적\s*손상|"
    r"치료가\s*필요|반드시\s*상담|진단받|고위험군)"
)


def _redact(content: str) -> str:
    redacted = PHONE_PATTERN.sub("[연락처 가림]", content)
    redacted = EMAIL_PATTERN.sub("[이메일 가림]", redacted)
    redacted = URL_PATTERN.sub("[주소 가림]", redacted)
    return redacted


def evaluate_safety(source_type: str, content: str) -> SafetyFilterResult:
    normalized = content.strip()
    reasons: list[str] = []
    personal_info_detected = False

    if PHONE_PATTERN.search(normalized):
        reasons.append("contact_info")
        personal_info_detected = True
    if EMAIL_PATTERN.search(normalized):
        reasons.append("email")
        personal_info_detected = True
    if URL_PATTERN.search(normalized):
        reasons.append("url")
        personal_info_detected = True
    if AFFILIATION_PATTERN.search(normalized):
        reasons.append("identifying_info")
        personal_info_detected = True
    if SPECIFIC_EVENT_PATTERN.search(normalized):
        reasons.append("specific_event")
        personal_info_detected = True

    crisis_expression_detected = bool(CRISIS_PATTERN.search(normalized))
    abusive = bool(ABUSE_PATTERN.search(normalized))
    medical_assertion = bool(MEDICAL_ASSERTION_PATTERN.search(normalized))

    if crisis_expression_detected:
        reasons.append("crisis_expression")
    if abusive:
        reasons.append("abuse_or_attack")
    if medical_assertion:
        reasons.append("medical_assertion")

    redacted = _redact(normalized)
    content_redacted = redacted if redacted != normalized else None

    if crisis_expression_detected or abusive:
        return SafetyFilterResult(
            safety_status=SafetyStatus.EXCLUDE.value,
            public_status=PublicStatus.EXCLUDED.value,
            moderation_reason=",".join(dict.fromkeys(reasons)),
            content_redacted=content_redacted,
            crisis_expression_detected=crisis_expression_detected,
            personal_info_detected=personal_info_detected,
        )

    if personal_info_detected or medical_assertion:
        return SafetyFilterResult(
            safety_status=SafetyStatus.REVIEW.value,
            public_status=PublicStatus.PENDING.value,
            moderation_reason=",".join(dict.fromkeys(reasons)),
            content_redacted=content_redacted,
            crisis_expression_detected=False,
            personal_info_detected=personal_info_detected,
        )

    return SafetyFilterResult(
        safety_status=SafetyStatus.SAFE.value,
        public_status=PublicStatus.PUBLIC.value,
        moderation_reason=None,
        content_redacted=None,
        crisis_expression_detected=False,
        personal_info_detected=False,
    )
