import pytest

from app.config import settings
from app.schemas.user import UserCreate
from app.services.user import create_user


async def test_register_is_disabled(client):
    response = await client.post(
        "/auth/register",
        json={
            "name": "New User",
            "username": "newbie",
            "email": "newbie@example.com",
            "password": "supersecret123",
        },
    )
    assert response.status_code == 403
    body = response.json()
    assert "Google or GitHub" in body["detail"]


@pytest.mark.skip(reason="POST /auth/register is disabled; duplicate-check unreachable via HTTP")
async def test_duplicate_username_returns_409(client):
    payload = {
        "name": "A",
        "username": "dupe",
        "email": "a@example.com",
        "password": "password123",
    }
    await client.post("/auth/register", json=payload)
    payload["email"] = "b@example.com"
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 409


async def test_login_accepts_email_or_username(client, session):
    # Registration is disabled at the API layer; create the pre-existing
    # password account directly via the service layer to test login.
    await create_user(
        session,
        UserCreate(
            name="A",
            username="flexible",
            email="flexible@example.com",
            password="password123",
        ),
    )
    for identifier in ("flexible", "flexible@example.com"):
        response = await client.post(
            "/auth/login", data={"username": identifier, "password": "password123"}
        )
        assert response.status_code == 200


async def test_protected_route_rejects_missing_token(client):
    assert (await client.get("/watchlist")).status_code == 401


async def test_me_returns_current_user(auth_client):
    response = await auth_client.get("/auth/me")
    assert response.status_code == 200
    assert response.json()["username"] == "tester"


async def test_oauth_login_requires_internal_secret(client):
    response = await client.post(
        "/auth/oauth",
        json={"email": "oauth@example.com", "name": "OAuth User", "provider": "google"},
    )
    assert response.status_code == 403


async def test_oauth_login_rejects_wrong_secret(client):
    response = await client.post(
        "/auth/oauth",
        json={"email": "oauth@example.com", "name": "OAuth User", "provider": "google"},
        headers={"X-Internal-Auth-Secret": "wrong-secret"},
    )
    assert response.status_code == 403


async def test_oauth_login_creates_user_and_returns_token(client):
    response = await client.post(
        "/auth/oauth",
        json={"email": "oauth@example.com", "name": "OAuth User", "provider": "google"},
        headers={"X-Internal-Auth-Secret": settings.internal_auth_secret},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
