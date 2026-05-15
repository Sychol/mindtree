from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.schemas.display import DisplayKeyword, DisplaySnapshotResponse
from app.services.display import heartbeat_event, snapshot_to_event
from app.services.sse import format_sse_event


def test_format_sse_event_serializes_keyword_snapshot() -> None:
    event = format_sse_event(
        "keyword_snapshot",
        {
            "eventSlug": "fire-expo-2026",
            "participantCount": 1,
            "completedCount": 1,
            "cloudKeywords": [{"text": "쉼", "weight": 3, "category": "support"}],
            "generatedAt": datetime(2026, 5, 13, 9, 0, tzinfo=timezone.utc),
        },
    )

    assert event.startswith("event: keyword_snapshot\n")
    assert 'data: {"eventSlug":"fire-expo-2026"' in event
    assert event.endswith("\n\n")


def test_snapshot_and_heartbeat_events_are_privacy_safe() -> None:
    snapshot = DisplaySnapshotResponse(
        eventSlug="fire-expo-2026",
        participantCount=2,
        completedCount=1,
        topMindKeywords=[],
        topSupportKeywords=[DisplayKeyword(text="쉼", weight=3)],
        cloudKeywords=[DisplayKeyword(text="쉼", weight=3, category="support")],
        generatedAt=datetime.now(timezone.utc),
    )
    payload = snapshot_to_event(snapshot) + heartbeat_event()

    assert "event: keyword_snapshot" in payload
    assert "event: heartbeat" in payload
    for token in [
        "content_raw",
        "contentRedacted",
        "session_id",
        "completionCode",
        "scaleScores",
        "riskFlags",
        "safety_status",
        "public_status",
    ]:
        assert token not in payload


def test_stream_endpoint_returns_event_stream_content_type(monkeypatch, client: TestClient, event_factory) -> None:
    async def finite_stream(**kwargs):
        del kwargs
        yield format_sse_event("heartbeat", {"status": "ok"})

    monkeypatch.setattr("app.api.routes.display.stream_display_snapshots", finite_stream)
    event = event_factory()

    response = client.get(f"/api/events/{event.slug}/stream")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: heartbeat" in response.text
