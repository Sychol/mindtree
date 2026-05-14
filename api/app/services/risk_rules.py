from dataclasses import dataclass
from typing import Any

from app.services.scoring import RULE_VERSION, ScaleScoreResult


@dataclass(frozen=True)
class RiskFlagResult:
    phq9_item9_positive: bool
    crisis_expression_detected: bool
    trauma_high_signal: bool
    moral_injury_high_signal: bool
    public_restriction: bool
    help_notice_required: bool
    details: dict[str, Any]
    rule_version: str = RULE_VERSION


def calculate_risk_flags(scale_scores: list[ScaleScoreResult]) -> RiskFlagResult:
    by_scale = {score.scale_code: score for score in scale_scores}

    phq9 = by_scale["phq9"]
    pcl5 = by_scale["pcl5"]
    kmies = by_scale["kmies"]
    kscs = by_scale["kscs"]

    phq9_total_score = int(phq9.sub_scores["total_score"])
    phq9_item9_score = int(phq9.sub_scores["item9_score"])
    pcl5_total_score = int(pcl5.sub_scores["total_score"])
    kmies_total_score = int(kmies.sub_scores["total_score"])

    phq9_item9_positive = phq9_item9_score >= 1
    trauma_high_signal = pcl5_total_score >= 34
    moral_injury_high_signal = kmies_total_score >= 37

    details: dict[str, Any] = {
        "kscs_level": kscs.severity_level,
    }
    if phq9_total_score >= 16:
        details["phq9_high_instability_signal"] = True
    if phq9_total_score >= 20 and phq9_item9_positive:
        details["phq9_severe_with_item9"] = True
    if 31 <= pcl5_total_score <= 33:
        details["pcl5_threshold_signal"] = True

    return RiskFlagResult(
        phq9_item9_positive=phq9_item9_positive,
        crisis_expression_detected=False,
        trauma_high_signal=trauma_high_signal,
        moral_injury_high_signal=moral_injury_high_signal,
        public_restriction=phq9_item9_positive,
        help_notice_required=phq9_item9_positive,
        details=details,
    )
