from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.schemas.display import DisplayKeyword, DisplaySnapshotResponse
from app.services.display import heartbeat_event, snapshot_to_event
from app.services.sse import format_sse_event

FORBIDDEN_SSE_TOKENS = [
    "content_raw",
    "contentRaw",
    "contentRedacted",
    "session_id",
    "sessionId",
    "completionCode",
    "scaleScores",
    "riskFlags",
    "safety_status",
    "public_status",
    "moderation_reason",
    "reviewed_by",
]


def _assert_no_forbidden_tokens(payload: str) -> None:
    for token in FORBIDDEN_SSE_TOKENS:
        assert token not in payload


def test_sse_keyword_snapshot_and_heartbeat_events_are_contract_safe() -> None:
    snapshot = DisplaySnapshotResponse(
        eventSlug="fire-expo-2026",
        participantCount=3,
        completedCount=2,
        topMindKeywords=[DisplayKeyword(text="calm", weight=3)],
        topSupportKeywords=[DisplayKeyword(text="support", weight=2)],
        cloudKeywords=[
            DisplayKeyword(text="calm", weight=3, category="mind_signal"),
            DisplayKeyword(text="support", weight=2, category="support"),
        ],
        generatedAt=datetime.now(timezone.utc),
    )

    payload = snapshot_to_event(snapshot) + heartbeat_event()

    assert "event: keyword_snapshot" in payload
    assert "event: heartbeat" in payload
    assert "calm" in payload
    _assert_no_forbidden_tokens(payload)


def test_sse_stream_endpoint_can_return_finite_event_stream(monkeypatch, client: TestClient, event_factory) -> None:
    async def finite_stream(**kwargs):
        del kwargs
        yield format_sse_event("heartbeat", {"status": "ok"})

    monkeypatch.setattr("app.api.routes.display.stream_display_snapshots", finite_stream)
    event = event_factory()

    response = client.get(f"/api/events/{event.slug}/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: heartbeat" in response.text
    _assert_no_forbidden_tokens(response.text)
