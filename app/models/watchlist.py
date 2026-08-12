from typing import TYPE_CHECKING
from datetime import datetime
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, UniqueConstraint, CheckConstraint, Enum, DateTime, func
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.anime import Anime
    from app.models.user import User

class WatchStatus(enum.StrEnum):
    WATCHING = "watching" 
    COMPLETED = "completed"
    DROPPED = "dropped"
    PLAN_TO_WATCH = "plan_to_watch"

class Watchlist(Base):
    __tablename__="watchlist"

    __table_args__ = (
        UniqueConstraint("user_id", "anime_id", name="uq_watchlist_user_anime"),
        CheckConstraint("score >= 1 AND score <= 10", name="ck_watchlist_score_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    anime_id: Mapped[int] = mapped_column(ForeignKey("anime.id"))

    episodes_watched: Mapped[int] = mapped_column(default=0)
    status: Mapped[WatchStatus] = mapped_column(Enum(WatchStatus, name="watch_status", values_callable=lambda e: [m.value for m in e]), default=WatchStatus.PLAN_TO_WATCH)

    score: Mapped[int|None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    anime: Mapped["Anime"] = relationship(back_populates="watchlist_entries")
    user: Mapped["User"] = relationship(back_populates="watchlist_entries")