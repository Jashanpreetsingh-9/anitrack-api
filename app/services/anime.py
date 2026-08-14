from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.clients.anime_source import fetch_anime, to_anime_fields
from app.clients.anime_source import search_anime as anime_search
from app.models.anime import Anime
from app.models.genre import Genre


async def get_anime(session: AsyncSession, anime_id: int) -> Anime | None:
    stmt = select(Anime).where(Anime.id == anime_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_anime_by_jikan_id(session: AsyncSession, jikan_id: int) -> Anime | None:
    stmt = select(Anime).where(Anime.jikan_id == jikan_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def import_anime(session: AsyncSession, jikan_id: int) -> Anime:
    """Return the local Anime for this Jikan ID, importing it if we don't have it."""
    existing = await get_anime_by_jikan_id(session, jikan_id)
    if existing is not None:
        return existing
    data = await fetch_anime(jikan_id)
    anime = Anime(**to_anime_fields(data))
    session.add(anime)
    await session.commit()
    await session.refresh(anime)
    return anime


async def search(query: str, limit: int = 20) -> list[dict]:
    results = await anime_search(query, limit)
    return [to_anime_fields(item) for item in results]


async def _get_or_create_genres(session: AsyncSession, genre_names: list[str]) -> list[Genre]:
    if not genre_names:
        return []

    existing = await session.execute(select(Genre).where(Genre.name.in_(genre_names)))
    existing_genres = {g.name: g for g in existing.scalars()}

    genres = []
    for name in genre_names:
        if name in existing_genres:
            genres.append(existing_genres[name])
        else:
            genre = Genre(name=name)
            session.add(genre)
            genres.append(genre)

    await session.flush()  # assigns IDs to newly created genres before use
    return genres


async def upsert_anime(session: AsyncSession, raw: dict) -> Anime:
    """Fetch-and-overwrite, for catalog syncing. Unlike import_anime, this
    always refreshes score/rank/popularity even if the row already exists."""
    fields = to_anime_fields(raw)
    genre_names = [g["name"] for g in raw.get("genres", [])]

    stmt = (
        pg_insert(Anime)
        .values(
            jikan_id=fields["jikan_id"],
            title=fields["title"],
            synopsis=fields["synopsis"],
            image_url=fields["image_url"],
            episodes=fields["episodes"],
            is_airing=fields["is_airing"],
            score=raw.get("score"),
            rank=raw.get("rank"),
            popularity=raw.get("popularity"),
            season=raw.get("season"),
            year=raw.get("year"),
        )
        .on_conflict_do_update(
            index_elements=["jikan_id"],
            set_={
                "title": fields["title"],
                "synopsis": fields["synopsis"],
                "image_url": fields["image_url"],
                "episodes": fields["episodes"],
                "is_airing": fields["is_airing"],
                "score": raw.get("score"),
                "rank": raw.get("rank"),
                "popularity": raw.get("popularity"),
                "season": raw.get("season"),
                "year": raw.get("year"),
            },
        )
        .returning(Anime)
    )
    result = await session.execute(stmt)
    anime = result.scalar_one()

    genres = await _get_or_create_genres(session, genre_names)

    await session.refresh(anime, attribute_names=["genres"])
    anime.genres = genres

    await session.commit()
    return anime


async def get_explore(
    session: AsyncSession,
    genre: str | None = None,
    season: str | None = None,
    page: int = 1,
    page_size: int = 24,
) -> list[Anime]:
    query = select(Anime).options(selectinload(Anime.genres))

    if genre:
        query = query.join(Anime.genres).where(Genre.name == genre)
    if season:
        query = query.where(Anime.season == season)

    query = query.order_by(Anime.rank.asc().nulls_last())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    return list(result.scalars().unique())
