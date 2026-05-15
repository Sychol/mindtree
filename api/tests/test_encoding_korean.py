import json
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]


def test_questions_seed_is_utf8_and_korean_text_is_readable() -> None:
    path = ROOT / "docs" / "data" / "questions_fire_expo_2026_final_260515.json"

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert data["metadata"]["encoding"].lower() == "utf-8"
    assert data["metadata"]["questionCount"] == 61
    assert data["metadata"]["ruleVersion"] == "v3-2026-05-15-final-questions"
    assert len(data["questions"]) == 61

    assert "귀하의 연령대는 어떻게 되십니까?" in raw
    assert "차라리 죽는 것이 낫겠다는 생각이 들거나" in raw
    assert "거의 그렇지 않다" in raw
    assert "占" not in raw


def test_scoring_rules_seed_is_utf8_and_korean_text_is_readable() -> None:
    path = ROOT / "docs" / "data" / "scoring_rules_v3_final_260515.json"

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    assert data["ruleVersion"] == "v3-2026-05-15-final-questions"
    assert "profile" in data["scaleMetadata"]
    assert "phq9" in data["scaleMetadata"]
    assert "pcl5" in data["scaleMetadata"]
    assert "kmies" in data["scaleMetadata"]
    assert "kscs" in data["scaleMetadata"]

    assert "K-MIES는 최종본에서 6문항으로 변경" in raw
    assert "K-SCS는 최종본에서 12문항 short-form으로 변경" in raw
    assert "占" not in raw


def test_public_event_korean_notices_are_readable(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.get(f"/api/events/{event.slug}/public")

    assert response.status_code == 200
    assert "占" not in response.text

    data = response.json()
    assert data["notices"]["notDiagnosis"]
    assert data["notices"]["anonymousKeywordDisplay"]
