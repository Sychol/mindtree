from dataclasses import dataclass
from typing import Iterable

from app.models.risk import RiskFlag
from app.models.score import ScaleScore

DEFAULT_HELP_NOTICE_TEXT = (
    "지금 자신을 해치고 싶은 생각이 들거나 혼자 감당하기 어렵다면, "
    "가까운 사람이나 현장 운영자에게 바로 도움을 요청해 주세요. "
    "이 안내는 진단이나 치료가 아니라 안전을 위한 안내입니다."
)


@dataclass(frozen=True)
class TemplateSummary:
    template_text: str
    signals: list[str]
    recommended_action: str
    help_notice_required: bool
    risk_notice_text: str | None


def _by_scale(scale_scores: Iterable[ScaleScore]) -> dict[str, ScaleScore]:
    return {scale_score.scale_code: scale_score for scale_score in scale_scores}


def _phq9_signal(severity_level: str | None) -> str:
    if severity_level == "no_specific_findings":
        return "최근 기분과 활력에서 큰 부담 신호는 두드러지지 않습니다."
    if severity_level == "mild_depressive_symptoms":
        return "최근 기분이나 활력에 약한 부담 신호가 있을 수 있습니다."
    if severity_level == "moderate_depression_suspected":
        return "최근 기분과 일상 에너지에 부담이 커졌을 수 있습니다."
    if severity_level == "severe_depression_score_range":
        return "최근 기분과 활력의 부담이 꽤 크게 느껴질 수 있습니다."
    return "최근 기분과 활력의 변화를 살펴볼 필요가 있습니다."


def _pcl5_signal(severity_level: str | None) -> str:
    if severity_level == "normal_range":
        return "반복적으로 떠오르는 장면이나 몸의 긴장 신호는 낮은 편일 수 있습니다."
    if severity_level == "threshold":
        return "특정 경험이 떠오를 때 마음과 몸이 예민하게 반응하는 신호가 있을 수 있습니다."
    if severity_level == "high_risk":
        return "반복적으로 떠오르는 생각이나 긴장 반응이 꽤 크게 남아 있을 수 있습니다."
    return "몸과 마음이 특정 경험에 반응하는 방식을 살펴볼 필요가 있습니다."


def _kmies_signal(severity_level: str | None) -> str:
    if severity_level == "low":
        return "책임감이나 자기비난의 부담은 비교적 낮은 편일 수 있습니다."
    if severity_level == "moderate":
        return "어떤 장면이나 판단이 마음에 남아 책임감이나 불편감으로 이어질 수 있습니다."
    if severity_level == "high":
        return "책임감, 자기비난, 신뢰와 관련된 마음의 부담이 무겁게 남아 있을 수 있습니다."
    return "책임감이나 불편감이 마음에 남아 있는지 살펴볼 필요가 있습니다."


def _kscs_signal(severity_level: str | None) -> str:
    if severity_level == "low":
        return "지금은 스스로에게 조금 더 부드럽게 말해보는 연습이 도움이 될 수 있습니다."
    if severity_level == "medium":
        return "상황에 따라 스스로를 돌보는 힘이 있지만, 큰 부담 앞에서는 자기비판이 올라올 수 있습니다."
    if severity_level == "high":
        return "어려운 순간에도 자신을 돌보려는 회복 자원이 비교적 잘 작동하고 있을 수 있습니다."
    return "스스로를 돌보는 힘이 어떤 방식으로 작동하는지 살펴볼 필요가 있습니다."


def build_template_summary(
    scale_scores: list[ScaleScore],
    risk_flag: RiskFlag,
) -> TemplateSummary:
    scores = _by_scale(scale_scores)
    signals = [
        _phq9_signal(scores.get("phq9").severity_level if scores.get("phq9") else None),
        _pcl5_signal(scores.get("pcl5").severity_level if scores.get("pcl5") else None),
        _kmies_signal(scores.get("kmies").severity_level if scores.get("kmies") else None),
        _kscs_signal(scores.get("kscs").severity_level if scores.get("kscs") else None),
    ]

    headline = "최근 마음에 긴장 신호가 나타납니다."
    if scores.get("phq9") and scores["phq9"].severity_level == "no_specific_findings":
        headline = "최근 마음 상태에서 큰 부담 신호는 두드러지지 않습니다."
    if risk_flag.help_notice_required or risk_flag.public_restriction:
        headline = "최근 마음에 돌봄이 필요한 신호가 나타납니다."

    recommended_action = (
        "잠시 숨을 고르고, 믿을 수 있는 사람에게 현재 상태를 말해보는 것이 도움이 될 수 있습니다."
    )
    if scores.get("kscs") and scores["kscs"].severity_level == "high":
        recommended_action = "이미 가진 회복 자원을 떠올리며, 오늘 가능한 작은 쉼을 하나 선택해 보세요."
    elif risk_flag.help_notice_required:
        recommended_action = "혼자 감당하기 어렵다면 가까운 사람이나 현장 운영자에게 도움을 요청해 주세요."

    template_text = " ".join([headline, *signals, recommended_action])
    show_help_notice = bool(
        risk_flag.help_notice_required
        or risk_flag.public_restriction
        or risk_flag.phq9_item9_positive
        or risk_flag.crisis_expression_detected
    )

    return TemplateSummary(
        template_text=template_text,
        signals=signals,
        recommended_action=recommended_action,
        help_notice_required=show_help_notice,
        risk_notice_text=DEFAULT_HELP_NOTICE_TEXT if show_help_notice else None,
    )
