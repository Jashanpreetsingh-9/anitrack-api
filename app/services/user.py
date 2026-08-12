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
    except IntegrityError:
        await session.rollback()
        raise ConflictError("Username or email already taken")
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession, identifier: str, password: str
) -> User | None:
    stmt = select(User).where(
        or_(User.email == identifier, User.username == identifier)
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user