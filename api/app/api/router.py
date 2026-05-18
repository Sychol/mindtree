from fastapi import APIRouter

from app.api.routes import (
    admin_audit_logs,
    admin_auth,
    admin_events,
    admin_keywords,
    admin_manual_content,
    admin_responses,
    admin_review,
    admin_rewards,
    answers,
    cards,
    completion,
    display,
    events,
    health,
    questions,
    replies,
    sessions,
    summaries,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(sessions.router, tags=["sessions"])
api_router.include_router(questions.router, tags=["questions"])
api_router.include_router(answers.router, tags=["answers"])
api_router.include_router(summaries.router, tags=["summaries"])
api_router.include_router(cards.router, tags=["cards"])
api_router.include_router(replies.router, tags=["replies"])
api_router.include_router(completion.router, tags=["completion"])
api_router.include_router(display.router, tags=["display"])
api_router.include_router(admin_auth.router, tags=["admin-auth"])
api_router.include_router(admin_events.router, tags=["admin-events"])
api_router.include_router(admin_manual_content.router, tags=["admin-manual-content"])
api_router.include_router(admin_review.router, tags=["admin-review"])
api_router.include_router(admin_keywords.router, tags=["admin-keywords"])
api_router.include_router(admin_responses.router, tags=["admin-responses"])
api_router.include_router(admin_rewards.router, tags=["admin-rewards"])
api_router.include_router(admin_audit_logs.router, tags=["admin-audit-logs"])
