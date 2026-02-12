from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.settings import settings

Base = declarative_base()

SHARD_ENGINES = {
    "shard0": create_async_engine(settings.DB_SHARD_0_URL, echo=True, pool_size=10, max_overflow=20),
    "shard1": create_async_engine(settings.DB_SHARD_1_URL, echo=True, pool_size=10, max_overflow=20),
    "shard2": create_async_engine(settings.DB_SHARD_2_URL, echo=True, pool_size=10, max_overflow=20),
}

# Example of how to get a session
async def get_session(shard_name: str) -> AsyncSession:
    engine = SHARD_ENGINES[shard_name]
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session