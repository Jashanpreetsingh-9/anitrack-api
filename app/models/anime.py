from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.genre import Genre
    from app.models.watchlist import Watchlist

anime_genres = Table(
    "anime_genres",
    Base.metadata,
    Column("anime_id", ForeignKey("anime.id"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id"), primary_key=True),
)


class Anime(Base):
    __tablename__ = "anime"

    id: Mapped[int] = mapped_column(primary_key=True)
    jikan_id: Mapped[int] = mapped_column(unique=True, index=True)

    title: Mapped[str]
    synopsis: Mapped[str | None]
    author: Mapped[str | None]
    image_url: Mapped[str | None]
    episodes: Mapped[int | None]
    is_airing: Mapped[bool] = mapped_column(default=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    popularity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    season: Mapped[str | None] = mapped_column(String(10), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    duration: Mapped[str | None] = mapped_column(String(30), nullable=True)
    type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trailer_youtube_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    trailer_embed_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    streaming_links: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)
    genres: Mapped[list[Genre]] = relationship(secondary=anime_genres, back_populates="anime")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    watchlist_entries: Mapped[list[Watchlist]] = relationship(back_populates="anime")
