import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.config import settings
from app.deps import CurrentUser, SessionDep
from app.schemas.user import OAuthLogin, ProfileSetup, Token, UserCreate, UserOut
from app.security import create_access_token
from app.services.user import authenticate_user, complete_profile, find_or_create_oauth_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(payload: UserCreate, session: SessionDep):
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Registration by email/password is disabled. Sign in with Google or GitHub.",
    )


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


@router.post("/oauth", response_model=Token)
async def oauth_login(
    payload: OAuthLogin,
    session: SessionDep,
    x_internal_auth_secret: Annotated[str | None, Header()] = None,
):
    if not x_internal_auth_secret or not secrets.compare_digest(
        x_internal_auth_secret, settings.internal_auth_secret
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    user = await find_or_create_oauth_user(session, payload.email, payload.name, payload.provider)
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def read_me(user: CurrentUser):
    return user


@router.post("/onboarding", response_model=UserOut)
async def finish_onboarding(payload: ProfileSetup, user: CurrentUser, session: SessionDep):
    return await complete_profile(session, user.id, payload.username, payload.password)
