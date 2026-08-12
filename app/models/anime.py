from typing import TYPE_CHECKING
from datetime import datetime
from app.models.base import Base
from sqlalchemy import DateTime, func
from sqlalchemy.orm import mapped_column, Mapped, relationship

if TYPE_CHECKING:
    from app.models.watchlist import Watchlist

class Anime(Base):
    __tablename__="anime"

    id: Mapped[int] = mapped_column(primary_key=True)
    jikan_id: Mapped[int] = mapped_column(unique=True,index=True)

    title: Mapped[str] 
    synopsis: Mapped[str|None]
    author: Mapped[str|None] 
    image_url: Mapped[str|None] 
    episodes: Mapped[int|None] 
    is_airing: Mapped[bool] = mapped_column(default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    watchlist_entries: Mapped[list["Watchlist"]] = relationship(back_populates="anime")
    



