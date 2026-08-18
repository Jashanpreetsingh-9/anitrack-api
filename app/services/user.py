from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError
from app.models.user import User
from app.schemas.user import UserCreate
from app.security import hash_password, verify_password


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    user = User(
        name=payload.name,
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Username or email already taken") from exc
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, identifier: str, password: str) -> User | None:
    stmt = select(User).where(or_(User.email == identifier, User.username == identifier))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or user.hashed_password is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def _unique_username_from(base: str, session: AsyncSession) -> str:
    candidate = base
    suffix = 1
    while True:
        result = await session.execute(select(User.id).where(User.username == candidate))
        if result.scalar_one_or_none() is None:
            return candidate
        suffix += 1
        candidate = f"{base}{suffix}"


async def find_or_create_oauth_user(
    session: AsyncSession, email: str, name: str, provider: str
) -> User:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is not None:
        if user.oauth_provider is None:
            raise ConflictError("An account already exists with this email")
        if user.oauth_provider != provider:
            raise ConflictError(f"This email is already registered via {user.oauth_provider}")
        return user

    base_username = email.split("@")[0]
    username = await _unique_username_from(base_username, session)

    user = User(
        name=name,
        username=username,
        email=email,
        hashed_password=None,
        oauth_provider=provider,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Username or email already taken") from exc
    await session.refresh(user)
    return user
