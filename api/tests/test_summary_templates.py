from types import SimpleNamespace

from app.services.summary_templates import build_template_summary

FORBIDDEN_EXPRESSIONS = [
    "우울증입니다",
    "PTSD입니다",
    "도덕적 손상입니다",
    "자살위험입니다",
    "고위험군입니다",
    "치료가 필요합니다",
    "반드시 상담을 받아야 합니다",
]


def _scale(scale_code: str, severity_level: str):
    return SimpleNamespace(scale_code=scale_code, severity_level=severity_level)


def _risk(**overrides):
    defaults = {
        "phq9_item9_positive": False,
        "crisis_expression_detected": False,
        "public_restriction": False,
        "help_notice_required": False,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def _summary(
    *,
    phq9: str = "no_specific_findings",
    pcl5: str = "normal_range",
    kmies: str = "low",
    kscs: str = "medium",
    risk=None,
):
    return build_template_summary(
        [
            _scale("phq9", phq9),
            _scale("pcl5", pcl5),
            _scale("kmies", kmies),
            _scale("kscs", kscs),
        ],
        risk or _risk(),
    )


def test_template_uses_phq9_mind_signal_language() -> None:
    assert "약한 부담 신호" in _summary(phq9="mild_depressive_symptoms").template_text
    assert "부담이 커졌을 수 있습니다" in _summary(phq9="moderate_depression_suspected").template_text
    assert "꽤 크게 느껴질 수 있습니다" in _summary(phq9="severe_depression_score_range").template_text


def test_template_uses_pcl5_mind_signal_language() -> None:
    assert "예민하게 반응하는 신호" in _summary(pcl5="threshold").template_text
    assert "긴장 반응이 꽤 크게" in _summary(pcl5="high_risk").template_text


def test_template_uses_kmies_mind_signal_language() -> None:
    assert "책임감이나 불편감" in _summary(kmies="moderate").template_text
    assert "마음의 부담이 무겁게" in _summary(kmies="high").template_text


def test_template_uses_kscs_recovery_resource_language() -> None:
    assert "부드럽게 말해보는 연습" in _summary(kscs="low").template_text
    assert "자기비판이 올라올 수 있습니다" in _summary(kscs="medium").template_text
    assert "회복 자원" in _summary(kscs="high").template_text


def test_help_notice_required_controls_risk_notice() -> None:
    summary = _summary(risk=_risk(help_notice_required=True))

    assert summary.help_notice_required is True
    assert summary.risk_notice_text is not None
    assert "안전" in summary.risk_notice_text


def test_template_text_avoids_forbidden_expressions() -> None:
    summary = _summary(
        phq9="severe_depression_score_range",
        pcl5="high_risk",
        kmies="high",
        kscs="low",
        risk=_risk(help_notice_required=True, public_restriction=True),
    )
    text = " ".join([summary.template_text, summary.risk_notice_text or ""])

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in text
