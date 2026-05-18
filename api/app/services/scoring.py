from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from app.models.answer import Answer
from app.models.question import Question

RULE_VERSION = "v4-2026-05-18-kmies-9-items"
K_SCS_REVERSE_QUESTION_NOS = [53, 56, 60, 61, 63, 64]

KMIES_QUESTION_NOS = list(range(15, 24))
PHQ9_QUESTION_NOS = list(range(24, 33))
PCL5_QUESTION_NOS = list(range(33, 53))
KSCS_QUESTION_NOS = list(range(53, 65))
PHQ9_ITEM9_QUESTION_NO = 32


@dataclass(frozen=True)
class ScaleScoreResult:
    scale_code: str
    raw_score: Decimal
    severity_level: str
    sub_scores: dict[str, Any]
    rule_version: str = RULE_VERSION


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _json_lookup(mapping: dict[str, Any], value: Any) -> Any | None:
    if value in mapping:
        return mapping[value]
    return mapping.get(str(value))


def calculate_answer_score(question: Question, answer_value: Any) -> Decimal | None:
    if not question.score_map:
        return None

    if question.question_type == "multi_select":
        if not isinstance(answer_value, list):
            return None
        total = Decimal("0")
        for item in answer_value:
            score = _json_lookup(question.score_map, item)
            if score is None:
                return None
            total += _decimal(score)
        return total

    score = _json_lookup(question.score_map, answer_value)
    if score is None:
        return None
    return _decimal(score)


def get_severity_level(scale_code: str, score: Decimal) -> str:
    if scale_code == "phq9":
        if score <= Decimal("4"):
            return "no_specific_findings"
        if score <= Decimal("9"):
            return "mild_depressive_symptoms"
        if score <= Decimal("19"):
            return "moderate_depression_suspected"
        return "severe_depression_score_range"

    if scale_code == "pcl5":
        if score <= Decimal("30"):
            return "normal_range"
        if score <= Decimal("33"):
            return "threshold"
        return "high_risk"

    if scale_code == "kmies":
        # K-MIES 9-item cutoffs are restored for the v4 9-item structure.
        if score <= Decimal("18"):
            return "low"
        if score <= Decimal("36"):
            return "moderate"
        return "high"

    if scale_code == "kscs":
        if score <= Decimal("2.4"):
            return "low"
        if score <= Decimal("3.5"):
            return "medium"
        return "high"

    raise ValueError(f"Unsupported scale code: {scale_code}")


def _answers_by_question_no(
    questions: list[Question],
    answers: list[Answer],
) -> dict[int, Answer]:
    question_id_to_no = {question.id: question.question_no for question in questions}
    return {
        question_id_to_no[answer.question_id]: answer
        for answer in answers
        if answer.question_id in question_id_to_no
    }


def _sum_score(question_nos: list[int], answer_by_no: dict[int, Answer]) -> Decimal:
    total = Decimal("0")
    for question_no in question_nos:
        answer = answer_by_no[question_no]
        total += _decimal(answer.score_value)
    return total


def calculate_phq9(answer_by_no: dict[int, Answer]) -> ScaleScoreResult:
    total = _sum_score(PHQ9_QUESTION_NOS, answer_by_no)
    item9_score = _decimal(answer_by_no[PHQ9_ITEM9_QUESTION_NO].score_value)

    return ScaleScoreResult(
        scale_code="phq9",
        raw_score=total,
        severity_level=get_severity_level("phq9", total),
        sub_scores={
            "total_score": int(total),
            "item9_question_no": PHQ9_ITEM9_QUESTION_NO,
            "item9_score": int(item9_score),
            "question_nos": PHQ9_QUESTION_NOS,
        },
    )


def calculate_pcl5(answer_by_no: dict[int, Answer]) -> ScaleScoreResult:
    total = _sum_score(PCL5_QUESTION_NOS, answer_by_no)
    return ScaleScoreResult(
        scale_code="pcl5",
        raw_score=total,
        severity_level=get_severity_level("pcl5", total),
        sub_scores={
            "total_score": int(total),
            "question_nos": PCL5_QUESTION_NOS,
        },
    )


def calculate_kmies(answer_by_no: dict[int, Answer]) -> ScaleScoreResult:
    total = _sum_score(KMIES_QUESTION_NOS, answer_by_no)
    return ScaleScoreResult(
        scale_code="kmies",
        raw_score=total,
        severity_level=get_severity_level("kmies", total),
        sub_scores={
            "total_score": int(total),
            "question_nos": KMIES_QUESTION_NOS,
        },
    )


def calculate_kscs(answer_by_no: dict[int, Answer]) -> ScaleScoreResult:
    total = Decimal("0")
    adjusted_scores: dict[str, float] = {}

    for question_no in KSCS_QUESTION_NOS:
        answer = answer_by_no[question_no]
        score = _decimal(answer.score_value)
        if question_no in K_SCS_REVERSE_QUESTION_NOS:
            score = Decimal("6") - score
        total += score
        adjusted_scores[str(question_no)] = float(score)

    mean_score = total / Decimal(len(KSCS_QUESTION_NOS))
    rounded_mean = mean_score.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)

    return ScaleScoreResult(
        scale_code="kscs",
        raw_score=mean_score,
        severity_level=get_severity_level("kscs", rounded_mean),
        sub_scores={
            "sum_score": float(total),
            "mean_score": float(mean_score),
            "rounded_mean_score": float(rounded_mean),
            "adjusted_scores": adjusted_scores,
            "question_nos": KSCS_QUESTION_NOS,
            "reverse_scored_question_nos": K_SCS_REVERSE_QUESTION_NOS,
        },
    )


def calculate_scale_scores(
    questions: list[Question],
    answers: list[Answer],
) -> list[ScaleScoreResult]:
    answer_by_no = _answers_by_question_no(questions, answers)

    return [
        calculate_phq9(answer_by_no),
        calculate_pcl5(answer_by_no),
        calculate_kmies(answer_by_no),
        calculate_kscs(answer_by_no),
    ]
