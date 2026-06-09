from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    APP_NAME: str = "CURE API"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/cure"
    MONGO_URL: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "cure"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    API_V1_STR: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["*"]
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_DEFAULT: int = 100
    ENVIRONMENT: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
