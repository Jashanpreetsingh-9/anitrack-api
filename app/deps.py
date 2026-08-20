from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import SessionLocal
from app.models.user import User
from app.security import decode_access_token
from app.services.user import get_user_by_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


async def get_session() -> AsyncGenerator[AsyncSession]:
    async with SessionLocal() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_user(
    session: SessionDep,
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error

    user = await get_user_by_id(session, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_user_id(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> int:
    """JWT-only auth — no DB lookup. For read endpoints where is_active staleness is OK."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_error
    return user_id


CurrentUserId = Annotated[int, Depends(get_current_user_id)]
