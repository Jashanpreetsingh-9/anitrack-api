import pytest

from app.errors import ConflictError
from app.models.user import User
from app.schemas.user import UserCreate
from app.security import hash_password
from app.services.user import (
    authenticate_user,
    complete_profile,
    create_user,
    find_or_create_oauth_user,
)


async def _make_password_user(session, username: str) -> User:
    user = User(
        name=username,
        username=username,
        email=f"{username}@example.com",
        hashed_password=hash_password("password123"),
        profile_complete=True,
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
    assert user.profile_complete is False


async def test_finds_existing_oauth_user_with_matching_provider(session):
    created = await find_or_create_oauth_user(session, "again@example.com", "Again", "github")
    found = await find_or_create_oauth_user(session, "again@example.com", "Again", "github")

    assert found.id == created.id


async def test_links_oauth_to_existing_password_account(session):
    existing = await _make_password_user(session, "pwuser")

    linked = await find_or_create_oauth_user(
        session, email=existing.email, name="New Name", provider="google"
    )

    assert linked.id == existing.id
    assert linked.oauth_provider == "google"
    assert linked.hashed_password is not None


async def test_allows_second_oauth_provider_for_same_email(session):
    created = await find_or_create_oauth_user(
        session, "switcher@example.com", "Switcher", "google"
    )

    found = await find_or_create_oauth_user(
        session, "switcher@example.com", "Switcher", "github"
    )

    assert found.id == created.id
    assert found.oauth_provider == "google"


async def test_generates_unique_username_on_collision(session):
    await _make_password_user(session, "taken")

    user = await find_or_create_oauth_user(session, "taken@other-domain.com", "Taken", "google")

    assert user.username != "taken"


async def test_create_user_rejects_duplicate_username(session):
    # POST /auth/register is disabled at the API layer, but create_user
    # itself is kept intact for reference and must still reject duplicates.
    payload = UserCreate(name="A", username="dupe", email="a@example.com", password="password123")
    await create_user(session, payload)

    duplicate = UserCreate(name="A", username="dupe", email="b@example.com", password="password123")
    with pytest.raises(ConflictError):
        await create_user(session, duplicate)


async def test_password_login_rejected_cleanly_for_oauth_only_account(session):
    await find_or_create_oauth_user(session, "oauthonly@example.com", "OAuth Only", "google")

    result = await authenticate_user(session, "oauthonly@example.com", "whatever")

    assert result is None


async def test_complete_profile_sets_username_and_password(session):
    user = await find_or_create_oauth_user(session, "setup@example.com", "Setup User", "google")

    completed = await complete_profile(session, user.id, "chosen_name", "password123")

    assert completed.username == "chosen_name"
    assert completed.profile_complete is True
    assert completed.hashed_password is not None

    logged_in = await authenticate_user(session, "chosen_name", "password123")
    assert logged_in is not None
    assert logged_in.id == user.id
