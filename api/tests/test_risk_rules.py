from decimal import Decimal

from app.services.risk_rules import calculate_risk_flags
from app.services.scoring import RULE_VERSION, ScaleScoreResult


def _scores(
    *,
    phq9_total: int = 0,
    phq9_item9: int = 0,
    pcl5_total: int = 0,
    kmies_total: int = 9,
    kscs_level: str = "medium",
) -> list[ScaleScoreResult]:
    return [
        ScaleScoreResult(
            scale_code="phq9",
            raw_score=Decimal(phq9_total),
            severity_level="no_specific_findings",
            sub_scores={"total_score": phq9_total, "item9_score": phq9_item9},
        ),
        ScaleScoreResult(
            scale_code="pcl5",
            raw_score=Decimal(pcl5_total),
            severity_level="normal_range",
            sub_scores={"total_score": pcl5_total},
        ),
        ScaleScoreResult(
            scale_code="kmies",
            raw_score=Decimal(kmies_total),
            severity_level="low",
            sub_scores={"total_score": kmies_total},
        ),
        ScaleScoreResult(
            scale_code="kscs",
            raw_score=Decimal("3.0"),
            severity_level=kscs_level,
            sub_scores={},
        ),
    ]


def test_phq9_item9_drives_help_notice_and_public_restriction() -> None:
    negative = calculate_risk_flags(_scores(phq9_item9=0))
    positive = calculate_risk_flags(_scores(phq9_item9=1))

    assert negative.phq9_item9_positive is False
    assert negative.help_notice_required is False
    assert negative.public_restriction is False

    assert positive.phq9_item9_positive is True
    assert positive.help_notice_required is True
    assert positive.public_restriction is True
    assert positive.crisis_expression_detected is False
    assert positive.rule_version == RULE_VERSION


def test_risk_details_and_high_signals() -> None:
    result = calculate_risk_flags(
        _scores(phq9_total=20, phq9_item9=1, pcl5_total=34, kmies_total=37, kscs_level="low")
    )

    assert result.trauma_high_signal is True
    assert result.moral_injury_high_signal is True
    assert result.details["phq9_high_instability_signal"] is True
    assert result.details["phq9_severe_with_item9"] is True
    assert result.details["kscs_level"] == "low"
    assert result.details["phq9_item9_question_no"] == 32
    assert result.details["kmies_high_signal_threshold"] == 37


def test_kmies_high_signal_uses_9_item_threshold() -> None:
    below = calculate_risk_flags(_scores(kmies_total=36))
    high = calculate_risk_flags(_scores(kmies_total=37))

    assert below.moral_injury_high_signal is False
    assert high.moral_injury_high_signal is True


def test_pcl5_threshold_signal_detail_without_high_signal() -> None:
    result = calculate_risk_flags(_scores(pcl5_total=32))

    assert result.trauma_high_signal is False
    assert result.details["pcl5_threshold_signal"] is True
