from pydantic import BaseModel, ConfigDict
from datetime import datetime

class AnimeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    jikan_id: int
    title: str
    synopsis: str|None
    author: str|None
    image_url: str|None
    episodes: int|None
    is_airing: bool

class AnimeCreate(BaseModel):
    jikan_id: int