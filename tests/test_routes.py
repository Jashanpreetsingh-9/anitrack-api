import pytest

from app.models.anime import Anime


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_search_requires_query(client):
    response = await client.get("/anime/search")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_search_limit_cap(client):
    response = await client.get("/anime/search", params={"q": "naruto", "limit": 100})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_anime_requires_auth(client):
    response = await client.post("/anime", json={"mal_id": 1})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_read_anime_internal_id_not_found(client):
    response = await client.get("/anime/999999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_watchlist_requires_auth(client):
    response = await client.get("/watchlist")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_recommendations_requires_auth(client):
    response = await client.get("/recommendations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_watchlist_crud(auth_client, session):
    anime = Anime(mal_id=42, title="Test Show")
    session.add(anime)
    await session.commit()

    create = await auth_client.post("/watchlist", json={"anime_id": anime.id})
    assert create.status_code == 201
    entry = create.json()
    entry_id = entry["id"]

    listing = await auth_client.get("/watchlist")
    assert listing.status_code == 200
    assert len(listing.json()) == 1

    patch = await auth_client.patch(
        f"/watchlist/{entry_id}",
        json={"episodes_watched": 3, "score": 8},
    )
    assert patch.status_code == 200
    assert patch.json()["episodes_watched"] == 3
    assert patch.json()["score"] == 8

    delete = await auth_client.delete(f"/watchlist/{entry_id}")
    assert delete.status_code == 204

    empty = await auth_client.get("/watchlist")
    assert empty.json() == []


@pytest.mark.asyncio
async def test_watchlist_invalid_score_returns_422(auth_client, session):
    anime = Anime(mal_id=99, title="Score Test")
    session.add(anime)
    await session.commit()

    create = await auth_client.post("/watchlist", json={"anime_id": anime.id})
    entry_id = create.json()["id"]

    response = await auth_client.patch(
        f"/watchlist/{entry_id}",
        json={"score": 11},
    )
    assert response.status_code == 422
