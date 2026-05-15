from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api").rstrip("/")
EVENT_SLUG = os.getenv("SMOKE_EVENT_SLUG", "fire-expo-2026")
TIMEOUT_SECONDS = float(os.getenv("SMOKE_TIMEOUT_SECONDS", "10"))

FORBIDDEN_DISPLAY_TOKENS = [
    "content_raw",
    "contentRaw",
    "content_redacted",
    "contentRedacted",
    "mindCardContent",
    "replyContent",
    "session_id",
    "sessionId",
    "resumeToken",
    "completionCode",
    "completion_code",
    "scale_scores",
    "scaleScores",
    "risk_flags",
    "riskFlags",
    "safety_status",
    "public_status",
    "moderation_reason",
    "reviewed_by",
    "admin",
]


@dataclass
class SmokeContext:
    client: httpx.Client
    session_id: str | None = None


class SmokeFailure(RuntimeError):
    pass


def _mask_code(code: str | None) -> str:
    if not code:
        return "-"
    if len(code) <= 5:
        return "***"
    return f"{code[:5]}***"


def _request(
    ctx: SmokeContext,
    method: str,
    path: str,
    *,
    step: str,
    **kwargs: Any,
) -> dict[str, Any]:
    response = ctx.client.request(method, f"{API_BASE_URL}{path}", **kwargs)
    if response.status_code >= 400:
        raise SmokeFailure(
            f"{step} failed status={response.status_code} body={response.text[:500]}"
        )
    if not response.content:
        return {}
    return response.json()


def _consent_payload(consent_version: str) -> dict[str, Any]:
    return {
        "consentVersion": consent_version,
        "acceptedItems": {
            "eventIsNotDiagnosis": True,
            "anonymousKeywordDisplay": True,
            "cardMayBeShownAnonymously": True,
            "noIdentifyingInfo": True,
            "adminModeration": True,
        },
    }


def _answer_value(question: dict[str, Any]) -> Any:
    options = question.get("options") or []
    question_type = question.get("questionType")
    if question.get("questionNo") == 3:
        return "q03_opt01"
    if question_type == "multi_select" and options:
        return [options[0]["value"]]
    if options:
        return options[0]["value"]
    if question_type == "number":
        return 0
    return "field smoke test safe response"


def _answers_payload(questions: list[dict[str, Any]]) -> dict[str, Any]:
    last_question_no = questions[-1]["questionNo"] if questions else None
    return {
        "answers": [
            {
                "questionId": question["id"],
                "answerValue": _answer_value(question),
            }
            for question in questions
        ],
        "clientProgress": {"lastQuestionNo": last_question_no},
    }


def _assert_no_display_leak(snapshot_text: str) -> None:
    leaked = [token for token in FORBIDDEN_DISPLAY_TOKENS if token in snapshot_text]
    if leaked:
        raise SmokeFailure(f"display snapshot leaked forbidden fields: {', '.join(leaked)}")


def run_smoke_flow() -> None:
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        ctx = SmokeContext(client=client)

        event = _request(ctx, "GET", f"/events/{EVENT_SLUG}/public", step="public event")
        if event["event"]["status"] != "open":
            raise SmokeFailure(f"event is not open: {event['event']['status']}")
        print("ok public_event")

        session_response = _request(
            ctx,
            "POST",
            f"/events/{EVENT_SLUG}/sessions",
            step="create session",
            json={"clientMeta": {"smoke": True, "device": "api"}},
        )
        ctx.session_id = session_response["session"]["id"]
        print("ok session_created")

        _request(
            ctx,
            "POST",
            f"/sessions/{ctx.session_id}/consent",
            step="consent",
            json=_consent_payload(event["event"]["consentVersion"]),
        )
        print("ok consent")

        questions_response = _request(
            ctx,
            "GET",
            f"/events/{EVENT_SLUG}/questions",
            step="questions",
        )
        questions = questions_response["questions"]
        if not questions:
            raise SmokeFailure("expected questions, got 0")
        print(f"ok questions={len(questions)}")

        answers = _request(
            ctx,
            "PUT",
            f"/sessions/{ctx.session_id}/answers/bulk",
            step="answers bulk",
            json=_answers_payload(questions),
        )
        if answers["sessionStatus"] != "questions_completed":
            raise SmokeFailure(f"unexpected answers sessionStatus={answers['sessionStatus']}")
        print("ok answers_bulk")

        summary = _request(
            ctx,
            "GET",
            f"/sessions/{ctx.session_id}/summary",
            step="summary",
        )
        if not summary["summary"]["finalText"]:
            raise SmokeFailure("summary finalText is empty")
        print(f"ok summary mode={summary['summary']['generationMode']}")

        viewed = _request(
            ctx,
            "POST",
            f"/sessions/{ctx.session_id}/summary/viewed",
            step="summary viewed",
        )
        if viewed["sessionStatus"] != "summary_viewed":
            raise SmokeFailure(f"unexpected viewed sessionStatus={viewed['sessionStatus']}")
        print("ok summary_viewed")

        card = _request(
            ctx,
            "POST",
            f"/sessions/{ctx.session_id}/cards",
            step="create card",
            json={
                "promptType": "to_now_me",
                "content": "I can take one steady breath and continue safely.",
            },
        )
        if card["sessionStatus"] != "card_created":
            raise SmokeFailure(f"unexpected card sessionStatus={card['sessionStatus']}")
        print("ok card_created")

        public_cards = _request(
            ctx,
            "GET",
            f"/events/{EVENT_SLUG}/cards/public",
            step="public cards",
            params={"excludeSessionId": ctx.session_id, "limit": 10},
        )
        if not public_cards["cards"]:
            raise SmokeFailure("no public peer cards. Run seed_dev before smoke tests.")
        selected_card_id = public_cards["cards"][0]["id"]
        print("ok public_peer_card")

        _request(
            ctx,
            "POST",
            f"/sessions/{ctx.session_id}/selected-card",
            step="select card",
            json={"selectedCardId": selected_card_id},
        )
        print("ok selected_card")

        reply = _request(
            ctx,
            "POST",
            f"/sessions/{ctx.session_id}/replies",
            step="reply",
            json={
                "targetCardId": selected_card_id,
                "replyType": "comfort",
                "content": "Thank you for sharing this. I am cheering for your next small step.",
            },
        )
        if not reply["completion"]["eligible"]:
            raise SmokeFailure("reply did not make session completion eligible")
        print(f"ok reply completion={_mask_code(reply['completion']['code'])}")

        completion = _request(
            ctx,
            "GET",
            f"/sessions/{ctx.session_id}/completion-code",
            step="completion code",
        )
        print(f"ok completion_code={_mask_code(completion['completionCode']['code'])}")

        snapshot_response = client.get(f"{API_BASE_URL}/events/{EVENT_SLUG}/display/snapshot")
        if snapshot_response.status_code != 200:
            raise SmokeFailure(
                f"display snapshot failed status={snapshot_response.status_code} body={snapshot_response.text[:500]}"
            )
        _assert_no_display_leak(snapshot_response.text)
        print("ok display_snapshot_privacy")


def main() -> None:
    try:
        run_smoke_flow()
    except (httpx.HTTPError, SmokeFailure) as exc:
        print(f"smoke_failed {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

    print("smoke_complete")


if __name__ == "__main__":
    main()
