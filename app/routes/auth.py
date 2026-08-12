from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.deps import CurrentUser, SessionDep
from app.schemas.user import Token, UserCreate, UserOut
from app.security import create_access_token
from app.services.user import authenticate_user, create_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate, session: SessionDep):
    return await create_user(session, payload)


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: SessionDep,
):
    user = await authenticate_user(session, form.username, form.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def read_me(user: CurrentUser):
    return user