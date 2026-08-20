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

    me = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["profile_complete"] is False


async def test_onboarding_completes_profile(client):
    oauth = await client.post(
        "/auth/oauth",
        json={"email": "newbie@example.com", "name": "Newbie", "provider": "github"},
        headers={"X-Internal-Auth-Secret": settings.internal_auth_secret},
    )
    token = oauth.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.post(
        "/auth/onboarding",
        json={"username": "newbie_user", "password": "password123"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "newbie_user"
    assert body["profile_complete"] is True

    login = await client.post(
        "/auth/login",
        data={"username": "newbie_user", "password": "password123"},
    )
    assert login.status_code == 200
