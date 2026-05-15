from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.admin_test_utils import auth_headers, create_admin


def test_admin_login_success_and_me(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session, password="good-password")

    response = client.post(
        "/api/admin/auth/login",
        json={"email": admin.email, "password": "good-password"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["tokenType"] == "bearer"
    assert data["accessToken"]
    assert data["admin"]["email"] == admin.email

    me = client.get(
        "/api/admin/auth/me",
        headers={"Authorization": f"Bearer {data['accessToken']}"},
    )
    assert me.status_code == 200
    assert me.json()["admin"]["id"] == str(admin.id)


def test_admin_login_rejects_bad_password_and_unknown_email(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session, password="good-password")

    bad_password = client.post(
        "/api/admin/auth/login",
        json={"email": admin.email, "password": "bad-password"},
    )
    unknown = client.post(
        "/api/admin/auth/login",
        json={"email": "missing@example.com", "password": "bad-password"},
    )

    assert bad_password.status_code == 401
    assert unknown.status_code == 401
    assert bad_password.json()["error"]["code"] == "UNAUTHORIZED"
    assert unknown.json()["error"]["code"] == "UNAUTHORIZED"


def test_inactive_admin_cannot_login(
    client: TestClient,
    db_session: Session,
) -> None:
    admin = create_admin(db_session, password="good-password", is_active=False)

    response = client.post(
        "/api/admin/auth/login",
        json={"email": admin.email, "password": "good-password"},
    )

    assert response.status_code == 401


def test_admin_api_requires_valid_token(
    client: TestClient,
    db_session: Session,
    event_factory,
) -> None:
    event = event_factory()
    admin = create_admin(db_session)

    no_token = client.get(f"/api/admin/events/{event.slug}/dashboard")
    bad_token = client.get(
        f"/api/admin/events/{event.slug}/dashboard",
        headers={"Authorization": "Bearer not-a-token"},
    )
    good_token = client.get(
        f"/api/admin/events/{event.slug}/dashboard",
        headers=auth_headers(admin),
    )

    assert no_token.status_code == 401
    assert bad_token.status_code == 401
    assert good_token.status_code == 200
