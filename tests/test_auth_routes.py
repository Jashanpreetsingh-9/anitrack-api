async def test_register_returns_no_password_fields(client):
    response = await client.post(
        "/auth/register",
        json={
            "name": "New User",
            "username": "newbie",
            "email": "newbie@example.com",
            "password": "supersecret123",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert "password" not in body
    assert "hashed_password" not in body


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


async def test_login_accepts_email_or_username(client):
    await client.post(
        "/auth/register",
        json={
            "name": "A",
            "username": "flexible",
            "email": "flexible@example.com",
            "password": "password123",
        },
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
