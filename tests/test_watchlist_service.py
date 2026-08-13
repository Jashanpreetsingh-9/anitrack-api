import pytest

from app.errors import ConflictError, NotFoundError
from app.models.anime import Anime
from app.models.user import User
from app.models.watchlist import WatchStatus
from app.schemas.watchlist import WatchlistCreate, WatchlistUpdate
from app.security import hash_password
from app.services.watchlist import add_entry, get_entry, list_entries, update_entry


async def _make_user(session, username: str) -> User:
    user = User(
        name=username,
        username=username,
        email=f"{username}@example.com",
        hashed_password=hash_password("password123"),
    )
    session.add(user)
    await session.commit()
    return user


async def _make_anime(session, mal_id: int) -> Anime:
    anime = Anime(jikan_id=mal_id, title=f"Show {mal_id}")
    session.add(anime)
    await session.commit()
    return anime


async def test_users_cannot_read_each_others_entries(session):
    alice = await _make_user(session, "alice")
    bob = await _make_user(session, "bob")
    anime = await _make_anime(session, 1)

    entry = await add_entry(session, alice.id, WatchlistCreate(anime_id=anime.id))

    with pytest.raises(NotFoundError):
        await get_entry(session, entry.id, bob.id)


async def test_users_cannot_update_each_others_entries(session):
    alice = await _make_user(session, "alice")
    bob = await _make_user(session, "bob")
    anime = await _make_anime(session, 1)
    entry = await add_entry(session, alice.id, WatchlistCreate(anime_id=anime.id))

    with pytest.raises(NotFoundError):
        await update_entry(session, entry.id, bob.id, WatchlistUpdate(episodes_watched=99))


async def test_cannot_add_same_anime_twice(session):
    user = await _make_user(session, "alice")
    anime = await _make_anime(session, 1)

    await add_entry(session, user.id, WatchlistCreate(anime_id=anime.id))
    with pytest.raises(ConflictError):
        await add_entry(session, user.id, WatchlistCreate(anime_id=anime.id))


async def test_partial_update_leaves_other_fields_alone(session):
    user = await _make_user(session, "alice")
    anime = await _make_anime(session, 1)
    entry = await add_entry(
        session,
        user.id,
        WatchlistCreate(anime_id=anime.id, status=WatchStatus.WATCHING),
    )

    updated = await update_entry(session, entry.id, user.id, WatchlistUpdate(episodes_watched=5))

    assert updated.episodes_watched == 5
    assert updated.status == WatchStatus.WATCHING


async def test_list_only_returns_own_entries(session):
    alice = await _make_user(session, "alice")
    bob = await _make_user(session, "bob")
    anime = await _make_anime(session, 1)
    await add_entry(session, alice.id, WatchlistCreate(anime_id=anime.id))

    assert await list_entries(session, alice.id) != []
    assert await list_entries(session, bob.id) == []
