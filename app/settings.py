from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DB_SHARD_0_URL: str = "postgresql+asyncpg://user:password@localhost:5432/url_shortener"
    DB_SHARD_1_URL: str = "postgresql+asyncpg://user:password@localhost:5433/url_shortener"
    DB_SHARD_2_URL: str = "postgresql+asyncpg://user:password@localhost:5434/url_shortener"

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()