from fastapi import APIRouter, status

from app.deps import CurrentUser, CurrentUserId, SessionDep
from app.schemas.watchlist import WatchlistCreate, WatchlistOut, WatchlistUpdate
from app.services.watchlist import (
    add_entry,
    delete_entry,
    list_entries,
    update_entry,
)

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistOut])
async def read_watchlist(user_id: CurrentUserId, session: SessionDep):
    return await list_entries(session, user_id)


@router.post("", response_model=WatchlistOut, status_code=201)
async def create_entry(payload: WatchlistCreate, user: CurrentUser, session: SessionDep):
    return await add_entry(session, user.id, payload)


@router.patch("/{entry_id}", response_model=WatchlistOut)
async def patch_entry(
    entry_id: int,
    payload: WatchlistUpdate,
    user: CurrentUser,
    session: SessionDep,
):
    return await update_entry(session, entry_id, user.id, payload)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_entry(entry_id: int, user: CurrentUser, session: SessionDep):
    await delete_entry(session, entry_id, user.id)
