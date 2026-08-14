from pydantic import BaseModel


class GenreOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}


class AnimeOut(BaseModel):
    id: int
    jikan_id: int
    title: str
    synopsis: str | None
    image_url: str | None
    episodes: int | None
    is_airing: bool
    author: str | None
    score: float | None
    rank: int | None
    popularity: int | None
    season: str | None
    year: int | None
    genres: list[GenreOut]

    model_config = {"from_attributes": True}


class AnimeCreate(BaseModel):
    jikan_id: int


class AnimeSearchResult(BaseModel):
    jikan_id: int
    title: str
    synopsis: str | None
    image_url: str | None
    episodes: int | None
    is_airing: bool
