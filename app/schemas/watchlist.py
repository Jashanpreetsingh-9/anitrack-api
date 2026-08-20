from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.watchlist import WatchStatus
from app.schemas.anime import AnimeOut


class WatchlistCreate(BaseModel):
    anime_id: int
    status: WatchStatus = WatchStatus.PLAN_TO_WATCH


class WatchlistUpdate(BaseModel):
    status: WatchStatus | None = None
    episodes_watched: Annotated[int | None, Field(ge=0)] = None
    score: Annotated[int | None, Field(ge=1, le=10)] = None


class WatchlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: WatchStatus
    episodes_watched: int
    score: int | None
    anime: AnimeOut
    created_at: datetime
    updated_at: datetime
