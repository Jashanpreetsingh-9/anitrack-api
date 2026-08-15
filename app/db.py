from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=True,
    pool_pre_ping=True,
    pool_recycle=300,
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
