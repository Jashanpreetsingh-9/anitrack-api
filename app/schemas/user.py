from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str = Field(min_length=8)


class ProfileSetup(BaseModel):
    username: str = Field(min_length=3, max_length=30, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8)


class OAuthLogin(BaseModel):
    email: EmailStr
    name: str
    provider: Literal["google", "github"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    email: EmailStr
    profile_complete: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
