from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.card import MindCard
from app.models.enums import ContentOrigin
from tests.admin_test_utils import create_admin
from tests.test_cards_api import _session


def _manual_card(
    db_session: Session,
    event_id,
    *,
    content: str,
    safety_status: str = "safe",
    public_status: str = "public",
):
    admin = create_admin(db_session)
    card = MindCard(
        event_id=event_id,
        session_id=None,
        prompt_type="to_colleague",
        content_raw=content,
        safety_status=safety_status,
        public_status=public_status,
        origin=ContentOrigin.ADMIN_MANUAL.value,
        origin_tag="ops",
        created_by_admin_id=admin.id,
    )
    db_session.add(card)
    db_session.commit()
    db_session.refresh(card)
    return card


def test_safe_public_manual_card_is_included_in_public_list(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    manual_card = _manual_card(db_session, event.id, content="manual public card")

    response = client.get(
        f"/api/events/{event.slug}/cards/public",
        params={"excludeSessionId": str(session.id), "limit": 10},
    )

    assert response.status_code == 200
    cards = response.json()["cards"]
    assert [item["id"] for item in cards] == [str(manual_card.id)]
    assert "originTag" not in cards[0]
    assert "createdByAdminId" not in cards[0]


def test_hidden_and_excluded_manual_cards_are_excluded_from_public_list(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    _manual_card(db_session, event.id, content="visible")
    _manual_card(db_session, event.id, content="hidden", public_status="hidden")
    _manual_card(db_session, event.id, content="excluded", safety_status="exclude", public_status="excluded")

    response = client.get(f"/api/events/{event.slug}/cards/public", params={"limit": 10})

    assert response.status_code == 200
    assert [card["content"] for card in response.json()["cards"]] == ["visible"]


def test_manual_card_is_not_excluded_by_exclude_session_id(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    session = _session(db_session, event)
    manual_card = _manual_card(db_session, event.id, content="manual null session card")

    response = client.get(
        f"/api/events/{event.slug}/cards/public",
        params={"excludeSessionId": str(session.id), "limit": 10},
    )

    assert response.status_code == 200
    assert response.json()["cards"][0]["id"] == str(manual_card.id)
