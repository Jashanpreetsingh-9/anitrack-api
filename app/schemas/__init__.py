from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.watchlist import WatchStatus
from app.schemas.anime import AnimeOut


class WatchlistCreate(BaseModel):
    anime_id: int
    status: WatchStatus = WatchStatus.PLAN_TO_WATCH


class WatchlistUpdate(BaseModel):
    status: WatchStatus | None = None
    episodes_watched: int | None = None
    score: int | None = None


class WatchlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: WatchStatus
    episodes_watched: int
    score: int | None
    anime: AnimeOut
    created_at: datetime
    updated_at: datetime