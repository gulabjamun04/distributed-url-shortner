from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict
import os

class Settings(BaseSettings):
    DB_SHARD_0_URL: str = os.getenv("DB_SHARD_0_URL", "postgresql+asyncpg://user:password@db-shard-0:5432/url_shortener")
    DB_SHARD_1_URL: str = os.getenv("DB_SHARD_1_URL", "postgresql+asyncpg://user:password@db-shard-1:5432/url_shortener")
    DB_SHARD_2_URL: str = os.getenv("DB_SHARD_2_URL", "postgresql+asyncpg://user:password@db-shard-2:5432/url_shortener")

    model_config = SettingsConfigDict(env_file=".env", extra='ignore')

settings = Settings()