import json
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]


def test_questions_seed_is_utf8_and_korean_text_is_readable() -> None:
    path = ROOT / "docs" / "data" / "questions_fire_expo_2026_final_260518.json"

    raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)

    assert data["metadata"]["encoding"].lower() == "utf-8"
    assert data["metadata"]["questionCount"] == 64
    assert data["metadata"]["ruleVersion"] == "v4-2026-05-18-kmies-9-items"
    assert len(data["questions"]) == 64
    assert chr(0xFFFD) not in raw
    assert data["questions"][0]["title"]
    assert data["questions"][31]["riskTrigger"]["type"] == "phq9_item9_positive"


def test_scoring_rules_seed_is_utf8_and_korean_text_is_readable() -> None:
    path = ROOT / "docs" / "data" / "scoring_rules_v4_final_260518.json"

    raw = path.read_text(encoding="utf-8-sig")
    data = json.loads(raw)

    assert data["ruleVersion"] == "v4-2026-05-18-kmies-9-items"
    assert "profile" in data["scaleMetadata"]
    assert "phq9" in data["scaleMetadata"]
    assert "pcl5" in data["scaleMetadata"]
    assert "kmies" in data["scaleMetadata"]
    assert "kscs" in data["scaleMetadata"]
    assert data["scaleMetadata"]["kscs"]["reverseScoredQuestionNos"] == [53, 56, 60, 61, 63, 64]
    assert chr(0xFFFD) not in raw


def test_public_event_korean_notices_are_readable(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.get(f"/api/events/{event.slug}/public")

    assert response.status_code == 200
    assert chr(0xFFFD) not in response.text

    data = response.json()
    assert data["notices"]["notDiagnosis"]
    assert data["notices"]["anonymousKeywordDisplay"]
