import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.settings import settings

Base = declarative_base()

# Check if running locally for seeding script
IS_LOCAL = os.getenv("RUNNING_LOCALLY", "false").lower() == "true"

DB_SHARD_0_URL = "postgresql+asyncpg://user:password@localhost:5432/url_shortener" if IS_LOCAL else settings.DB_SHARD_0_URL
DB_SHARD_1_URL = "postgresql+asyncpg://user:password@localhost:5433/url_shortener" if IS_LOCAL else settings.DB_SHARD_1_URL
DB_SHARD_2_URL = "postgresql+asyncpg://user:password@localhost:5434/url_shortener" if IS_LOCAL else settings.DB_SHARD_2_URL

SHARD_ENGINES = {
    "shard0": create_async_engine(
        DB_SHARD_0_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo_pool=False
    ),
    "shard1": create_async_engine(
        DB_SHARD_1_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo_pool=False
    ),
    "shard2": create_async_engine(
        DB_SHARD_2_URL,
        pool_size=50,
        max_overflow=100,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo_pool=False
    ),
}


# Example of how to get a session
async def get_session(shard_name: str) -> AsyncSession:
    engine = SHARD_ENGINES[shard_name]
    async_session = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session
