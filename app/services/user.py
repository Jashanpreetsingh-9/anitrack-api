from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.errors import ConflictError
from app.models.user import User
from app.schemas.user import UserCreate
from app.security import hash_password, verify_password


def user_needs_onboarding(user: User) -> bool:
    return not user.profile_complete


async def get_user_by_id(session: AsyncSession, user_id: int) -> User | None:
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(session: AsyncSession, payload: UserCreate) -> User:
    user = User(
        name=payload.name,
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
        profile_complete=True,
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

    if user is None or user.hashed_password is None or not user.profile_complete:
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
            # Existing password-only account with a matching, provider-verified
            # email — link this OAuth identity to it rather than rejecting.
            # The password stays intact, so both login methods work afterward.
            user.oauth_provider = provider
            await session.commit()
            await session.refresh(user)
            return user
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
        profile_complete=False,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Username or email already taken") from exc
    await session.refresh(user)
    return user


async def complete_profile(
    session: AsyncSession, user_id: int, username: str, password: str
) -> User:
    user = await get_user_by_id(session, user_id)
    if user is None:
        raise ConflictError("User not found")
    if user.profile_complete:
        raise ConflictError("Profile is already complete")

    existing = await session.execute(select(User.id).where(User.username == username))
    taken_id = existing.scalar_one_or_none()
    if taken_id is not None and taken_id != user.id:
        raise ConflictError("Username already taken")

    user.username = username
    user.hashed_password = hash_password(password)
    user.profile_complete = True
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("Username already taken") from exc
    await session.refresh(user)
    return user
