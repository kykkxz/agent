from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///instance/insurance.db"
    JWT_SECRET_KEY: str = "jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    MODEL_DIR: Path = Path("data/models")
    LLM_API_KEY: str | None = None
    LLM_API_BASE: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    LLM_MODEL: str = "qwen-flash"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
settings.MODEL_DIR.mkdir(parents=True, exist_ok=True)

if settings.DATABASE_URL.startswith("sqlite:///"):
    sqlite_path = Path(settings.DATABASE_URL.removeprefix("sqlite:///"))
    if sqlite_path != Path(":memory:"):
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
