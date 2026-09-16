from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ABACUS_", extra="ignore")

    node_name: str = "abacus-node"
    store: Literal["sqlite", "redis"] = "sqlite"
    sqlite_path: str = "abacus.db"
    redis_url: str = "redis://localhost:6379/0"
    redis_key: str = "abacus:sum"


@lru_cache
def get_settings() -> Settings:
    return Settings()
