from app.models.enums import PublicStatus, SafetyStatus
from app.services.safety_filter import evaluate_safety


def test_safe_general_sentence_is_public() -> None:
    result = evaluate_safety("mind_card", "오늘은 조금 쉬어가도 괜찮다.")

    assert result.safety_status == SafetyStatus.SAFE.value
    assert result.public_status == PublicStatus.PUBLIC.value
    assert result.moderation_reason is None


def test_phone_number_is_review_pending() -> None:
    result = evaluate_safety("mind_card", "필요하면 010-1234-5678로 연락해 주세요.")

    assert result.safety_status == SafetyStatus.REVIEW.value
    assert result.public_status == PublicStatus.PENDING.value
    assert result.personal_info_detected is True
    assert "contact_info" in (result.moderation_reason or "")
    assert result.content_redacted is not None


def test_email_is_review_pending() -> None:
    result = evaluate_safety("reply", "제 메일은 hello@example.com 입니다.")

    assert result.safety_status == SafetyStatus.REVIEW.value
    assert result.public_status == PublicStatus.PENDING.value
    assert result.personal_info_detected is True


def test_url_is_review_pending() -> None:
    result = evaluate_safety("reply", "자세한 내용은 https://example.com 에 있습니다.")

    assert result.safety_status == SafetyStatus.REVIEW.value
    assert result.public_status == PublicStatus.PENDING.value
    assert result.personal_info_detected is True


def test_affiliation_like_text_is_review_pending() -> None:
    result = evaluate_safety("mind_card", "저는 홍길동입니다. 서울소방서에서 일합니다.")

    assert result.safety_status == SafetyStatus.REVIEW.value
    assert result.public_status == PublicStatus.PENDING.value
    assert result.personal_info_detected is True


def test_crisis_expression_is_excluded() -> None:
    result = evaluate_safety("mind_card", "오늘은 자살하고 싶다는 생각이 들었다.")

    assert result.safety_status == SafetyStatus.EXCLUDE.value
    assert result.public_status == PublicStatus.EXCLUDED.value
    assert result.crisis_expression_detected is True


def test_abuse_is_excluded_or_reviewed() -> None:
    result = evaluate_safety("reply", "그 사람은 정말 병신 같다.")

    assert result.safety_status in {SafetyStatus.EXCLUDE.value, SafetyStatus.REVIEW.value}
    assert result.public_status != PublicStatus.PUBLIC.value


def test_medical_assertion_is_review_pending() -> None:
    result = evaluate_safety("reply", "당신은 치료가 필요합니다.")

    assert result.safety_status == SafetyStatus.REVIEW.value
    assert result.public_status == PublicStatus.PENDING.value
