"""Application settings."""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "demo-key"
    database_url: str = "sqlite:///./cino_hr.db"
    app_title: str = "CINO HR API"
    app_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
