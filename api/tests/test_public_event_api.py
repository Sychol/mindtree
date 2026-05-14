import pytest
from fastapi.testclient import TestClient


def test_public_event_open_success(client: TestClient, event_factory) -> None:
    event = event_factory()

    response = client.get(f"/api/events/{event.slug}/public")

    assert response.status_code == 200
    data = response.json()
    assert data["event"]["slug"] == event.slug
    assert data["event"]["name"] == "마음나무"
    assert data["event"]["status"] == "open"
    assert data["event"]["consentVersion"] == "v1"
    assert data["event"]["settings"] == {
        "displayEnabled": True,
        "maxMindCardsPerSession": 3,
        "helpNoticeEnabled": True,
    }
    assert "llmEnabled" not in data["event"]["settings"]
    assert data["notices"]["notDiagnosis"]
    assert data["notices"]["anonymousKeywordDisplay"]


def test_public_event_not_found(client: TestClient) -> None:
    response = client.get("/api/events/missing-event/public")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "EVENT_NOT_FOUND"


@pytest.mark.parametrize("event_status", ["draft", "archived", "closed"])
def test_public_event_not_open_is_restricted(
    client: TestClient,
    event_factory,
    event_status: str,
) -> None:
    event = event_factory(status=event_status)

    response = client.get(f"/api/events/{event.slug}/public")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "EVENT_NOT_OPEN"
