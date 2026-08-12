from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anime import Anime
from app.clients.jikan import fetch_anime, to_anime_fields


async def get_anime(session: AsyncSession, anime_id: int) -> Anime|None:
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