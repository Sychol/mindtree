from decimal import Decimal
from uuid import uuid4

from app.models.answer import Answer
from app.services.scoring import (
    K_SCS_REVERSE_QUESTION_NOS,
    calculate_kmies,
    calculate_kscs,
    calculate_pcl5,
    calculate_phq9,
)


def _answer(score: int) -> Answer:
    return Answer(
        event_id=uuid4(),
        session_id=uuid4(),
        question_id=uuid4(),
        answer_value=score,
        score_value=Decimal(score),
    )


def _answer_by_no(start: int, scores: list[int]) -> dict[int, Answer]:
    return {
        question_no: _answer(score)
        for question_no, score in zip(range(start, start + len(scores)), scores)
    }


def test_phq9_severity_bands_and_item9_score() -> None:
    cases = [
        ([0, 0, 0, 0, 0, 0, 0, 0, 0], "no_specific_findings"),
        ([1, 1, 1, 1, 1, 0, 0, 0, 0], "mild_depressive_symptoms"),
        ([2, 2, 2, 2, 2, 0, 0, 0, 0], "moderate_depression_suspected"),
        ([3, 3, 3, 3, 3, 3, 2, 2, 1], "severe_depression_score_range"),
    ]

    for scores, expected in cases:
        result = calculate_phq9(_answer_by_no(14, scores))
        assert result.severity_level == expected

    item9_result = calculate_phq9(_answer_by_no(14, [0, 0, 0, 0, 0, 0, 0, 0, 1]))
    assert item9_result.sub_scores["item9_score"] == 1


def test_pcl5_severity_bands() -> None:
    assert calculate_pcl5(_answer_by_no(23, [0] * 20)).severity_level == "normal_range"
    assert calculate_pcl5(_answer_by_no(23, [2] * 11 + [1] * 9)).severity_level == "threshold"
    assert calculate_pcl5(_answer_by_no(23, [2] * 17 + [0] * 3)).severity_level == "high_risk"


def test_kmies_severity_bands() -> None:
    assert calculate_kmies(_answer_by_no(43, [1] * 9)).severity_level == "low"
    assert calculate_kmies(_answer_by_no(43, [3] * 9)).severity_level == "moderate"
    assert calculate_kmies(_answer_by_no(43, [5] * 9)).severity_level == "high"


def test_kscs_reverse_scoring_and_bands() -> None:
    low_scores = {
        question_no: _answer(5 if question_no in K_SCS_REVERSE_QUESTION_NOS else 1)
        for question_no in range(52, 78)
    }
    medium_scores = {question_no: _answer(3) for question_no in range(52, 78)}
    high_scores = {
        question_no: _answer(1 if question_no in K_SCS_REVERSE_QUESTION_NOS else 5)
        for question_no in range(52, 78)
    }

    low = calculate_kscs(low_scores)
    medium = calculate_kscs(medium_scores)
    high = calculate_kscs(high_scores)

    assert low.severity_level == "low"
    assert medium.severity_level == "medium"
    assert high.severity_level == "high"
    assert medium.sub_scores["adjusted_scores"]["53"] == 3.0
    assert high.sub_scores["adjusted_scores"]["53"] == 5.0
    assert high.sub_scores["reverse_scored_question_nos"] == K_SCS_REVERSE_QUESTION_NOS
