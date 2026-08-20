from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    title: str = Field(min_length=1)
    reason: str = Field(min_length=1)
