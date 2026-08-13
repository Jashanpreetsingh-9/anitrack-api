from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_session
from app.schemas.anime import AnimeCreate, AnimeOut, AnimeSearchResult
from app.services.anime import get_anime, import_anime, search

router = APIRouter(prefix="/anime", tags=["anime"])


@router.get("/search", response_model=list[AnimeSearchResult])
async def search_anime(q: str, limit: int = 20):
    return await search(q, limit)


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
