from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.errors import ConflictError, NotFoundError
from app.models.anime import Anime
from app.models.watchlist import Watchlist
from app.schemas.watchlist import WatchlistCreate, WatchlistUpdate


async def list_entries(session: AsyncSession, user_id: int) -> list[Watchlist]:
    stmt = (
        select(Watchlist)
        .where(Watchlist.user_id == user_id)
        .options(selectinload(Watchlist.anime))
        .order_by(Watchlist.updated_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_entry(session: AsyncSession, entry_id: int, user_id: int) -> Watchlist:
    stmt = (
        select(Watchlist)
        .where(Watchlist.id == entry_id, Watchlist.user_id == user_id)
        .options(selectinload(Watchlist.anime))
    )
    result = await session.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None:
        raise NotFoundError("Watchlist entry not found")
    return entry


async def add_entry(session: AsyncSession, user_id: int, payload: WatchlistCreate) -> Watchlist:
    anime = await session.get(Anime, payload.anime_id)
    if anime is None:
        raise NotFoundError("Anime not found")

    entry = Watchlist(
        user_id=user_id,
        anime_id=payload.anime_id,
        status=payload.status,
    )
    session.add(entry)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Already on your watchlist") from exc

    await session.refresh(entry, attribute_names=["anime"])
    return entry


async def update_entry(
    session: AsyncSession, entry_id: int, user_id: int, payload: WatchlistUpdate
) -> Watchlist:
    entry = await get_entry(session, entry_id, user_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)

    await session.commit()
    await session.refresh(entry, attribute_names=["anime"])
    return entry


async def delete_entry(session: AsyncSession, entry_id: int, user_id: int) -> None:
    entry = await get_entry(session, entry_id, user_id)
    await session.delete(entry)
    await session.commit()
