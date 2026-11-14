"""Shared settings. Both backends import `settings` from here."""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DATABASE_URL: str = "sqlite:///vitalis.db"
    CORS_ORIGINS: List[str] = ["http://localhost:8501", "http://localhost:8502"]


settings = Settings()
