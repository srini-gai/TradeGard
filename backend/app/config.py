import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(
            os.path.join(_PROJECT_ROOT, ".env"),
            os.path.join(_BACKEND_DIR, ".env"),
        ),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    upstox_api_key: str = ""
    upstox_api_secret: str = ""
    upstox_access_token: str = ""
    vite_api_url: str = "http://localhost:8000"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
