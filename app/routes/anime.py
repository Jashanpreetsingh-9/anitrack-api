from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.schemas.anime import AnimeCreate, AnimeOut, AnimeSearchResult
from app.services.anime import get_anime, get_explore, import_anime, search

router = APIRouter(prefix="/anime", tags=["anime"])


@router.get("/search", response_model=list[AnimeSearchResult])
async def search_anime(q: str, limit: int = 20):
    return await search(q, limit)


@router.get("/explore", response_model=list[AnimeOut])
async def explore_anime(
    session: Annotated[AsyncSession, Depends(get_session)],
    genre: str | None = None,
    season: str | None = None,
    is_airing: bool | None = None,
    page: int = 1,
):
    return await get_explore(session, genre=genre, season=season, is_airing=is_airing, page=page)


@router.get("/{anime_id}", response_model=AnimeOut)
async def read_anime(anime_id: int, session: Annotated[AsyncSession, Depends(get_session)]):
    anime = await get_anime(session, anime_id)
    if anime is None:
        raise HTTPException(status_code=404, detail="Anime not found")
    return anime


@router.post("", response_model=AnimeOut, status_code=201)
async def create_anime(
    payload: AnimeCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
):
    return await import_anime(session, payload.jikan_id)
