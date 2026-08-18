import pytest

from app.errors import ConflictError
from app.models.user import User
from app.security import hash_password
from app.services.user import authenticate_user, find_or_create_oauth_user


async def _make_password_user(session, username: str) -> User:
    user = User(
        name=username,
        username=username,
        email=f"{username}@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(user)
    await session.commit()
    return user


async def test_creates_new_oauth_user(session):
    user = await find_or_create_oauth_user(session, "new@example.com", "New Person", "google")

    assert user.id is not None
    assert user.email == "new@example.com"
    assert user.name == "New Person"
    assert user.oauth_provider == "google"
    assert user.hashed_password is None


async def test_finds_existing_oauth_user_with_matching_provider(session):
    created = await find_or_create_oauth_user(session, "again@example.com", "Again", "github")
    found = await find_or_create_oauth_user(session, "again@example.com", "Again", "github")

    assert found.id == created.id


async def test_rejects_oauth_login_for_existing_password_account(session):
    await _make_password_user(session, "pwuser")

    with pytest.raises(ConflictError):
        await find_or_create_oauth_user(session, "pwuser@example.com", "Pw User", "google")


async def test_rejects_mismatched_oauth_provider(session):
    await find_or_create_oauth_user(session, "switcher@example.com", "Switcher", "github")

    with pytest.raises(ConflictError):
        await find_or_create_oauth_user(session, "switcher@example.com", "Switcher", "google")


async def test_generates_unique_username_on_collision(session):
    await _make_password_user(session, "taken")

    user = await find_or_create_oauth_user(session, "taken@other-domain.com", "Taken", "google")

    assert user.username != "taken"


async def test_password_login_rejected_cleanly_for_oauth_only_account(session):
    await find_or_create_oauth_user(session, "oauthonly@example.com", "OAuth Only", "google")

    result = await authenticate_user(session, "oauthonly@example.com", "whatever")

    assert result is None
