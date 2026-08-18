from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    name: str
    username: str
    email: EmailStr
    password: str


class OAuthLogin(BaseModel):
    email: str
    name: str
    provider: Literal["google", "github"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    username: str
    email: EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
