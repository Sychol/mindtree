from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.cards import (
    CreateMindCardRequest,
    CreateMindCardResponse,
    DeleteMindCardResponse,
    MyMindCardsResponse,
    PublicMindCardsResponse,
    SelectCardRequest,
    SelectCardResponse,
    UpdateMindCardRequest,
    UpdateMindCardResponse,
)
from app.services.cards import (
    create_mind_card,
    delete_mind_card,
    list_my_cards,
    list_public_cards,
    select_peer_card,
    update_mind_card,
)

router = APIRouter()


@router.post("/sessions/{sessionId}/cards", response_model=CreateMindCardResponse)
def create_session_card(
    payload: CreateMindCardRequest,
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> CreateMindCardResponse:
    return create_mind_card(db, session_id, payload)


@router.get("/sessions/{sessionId}/cards", response_model=MyMindCardsResponse)
def read_session_cards(
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> MyMindCardsResponse:
    return list_my_cards(db, session_id)


@router.patch("/sessions/{sessionId}/cards/{cardId}", response_model=UpdateMindCardResponse)
def update_session_card(
    payload: UpdateMindCardRequest,
    session_id: UUID = Path(alias="sessionId"),
    card_id: UUID = Path(alias="cardId"),
    db: Session = Depends(get_db),
) -> UpdateMindCardResponse:
    return update_mind_card(db, session_id, card_id, payload)


@router.delete("/sessions/{sessionId}/cards/{cardId}", response_model=DeleteMindCardResponse)
def delete_session_card(
    session_id: UUID = Path(alias="sessionId"),
    card_id: UUID = Path(alias="cardId"),
    db: Session = Depends(get_db),
) -> DeleteMindCardResponse:
    return delete_mind_card(db, session_id, card_id)


@router.get("/events/{eventSlug}/cards/public", response_model=PublicMindCardsResponse)
def read_public_cards(
    event_slug: str = Path(alias="eventSlug"),
    exclude_session_id: UUID | None = Query(default=None, alias="excludeSessionId"),
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
) -> PublicMindCardsResponse:
    return list_public_cards(
        db,
        event_slug=event_slug,
        exclude_session_id=exclude_session_id,
        limit=limit,
    )


@router.post("/sessions/{sessionId}/selected-card", response_model=SelectCardResponse)
def select_session_card(
    payload: SelectCardRequest,
    session_id: UUID = Path(alias="sessionId"),
    db: Session = Depends(get_db),
) -> SelectCardResponse:
    return select_peer_card(db, session_id, payload)
