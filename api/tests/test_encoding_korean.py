import json
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]


def test_questions_seed_is_utf8_and_korean_text_is_readable() -> None:
    path = ROOT / "docs" / "data" / "questions_fire_expo_2026.json"

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert data["metadata"]["encoding"].lower() == "utf-8"
    assert data["metadata"]["questionCount"] == 77
    assert data["metadata"]["ruleVersion"] == "v2-2026-05-13-scale-cutoffs"
    assert len(data["questions"]) == 77

    assert "귀하의 연령대" in raw
    assert "한국판 우울 증상 척도" in raw
    assert "차라리 죽는 것이" in raw
    assert "한국판 외상 후 스트레스 장애 체크리스트" in raw
    assert "한국판 도덕손상 사건 척도" in raw
    assert "한국판 자기자비 척도" in raw
    assert "거의 그렇지 않다" in raw
    assert "거의 항상 그렇다" in raw
    assert "�" not in raw


def test_scoring_rules_seed_is_utf8_and_korean_text_is_readable() -> None:
    path = ROOT / "docs" / "data" / "scoring_rules_v1.json"

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert data["ruleVersion"] == "v2-2026-05-13-scale-cutoffs"
    assert "profile" in data["scaleMetadata"]
    assert "phq9" in data["scaleMetadata"]
    assert "pcl5" in data["scaleMetadata"]
    assert "kmies" in data["scaleMetadata"]
    assert "kscs" in data["scaleMetadata"]

    assert "한국판 우울 증상 척도" in raw
    assert "한국판 외상 후 스트레스 장애 체크리스트" in raw
    assert "한국판 도덕손상 사건 척도" in raw
    assert "한국판 자기자비 척도" in raw
    assert "�" not in raw


def test_public_event_korean_notices_are_readable(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.get(f"/api/events/{event.slug}/public")

    assert response.status_code == 200
    assert "�" not in response.text

    data = response.json()
    assert "진단" in data["notices"]["notDiagnosis"]
    assert "익명 키워드" in data["notices"]["anonymousKeywordDisplay"]
