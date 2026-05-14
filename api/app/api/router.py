from fastapi import APIRouter

from app.api.routes import answers, events, health, questions, sessions

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(sessions.router, tags=["sessions"])
api_router.include_router(questions.router, tags=["questions"])
api_router.include_router(answers.router, tags=["answers"])
