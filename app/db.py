from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
