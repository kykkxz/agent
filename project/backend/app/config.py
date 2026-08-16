from __future__ import annotations

from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_KB_DB = (
    PROJECT_ROOT
    / "database"
    / "transport-safety-kb"
    / "data"
    / "transport_safety_kb.sqlite3"
)
DEFAULT_CHROMA = (
    PROJECT_ROOT / "database" / "transport-safety-kb" / "data" / "rag_chroma"
)
DEFAULT_HAZARD_PROMPT = (
    Path(__file__).resolve().parent / "prompts" / "hazard_detection.txt"
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "蜀道安全助手"
    api_prefix: str = "/api/v1"
    secret_key: str = "shudao-dev-secret-change-me"
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 7
    database_url: str = f"sqlite:///{(Path(__file__).resolve().parents[1] / 'data' / 'app.db').as_posix()}"
    kb_db_path: str = str(DEFAULT_KB_DB)
    chroma_dir: str = str(DEFAULT_CHROMA)
    upload_dir: str = str(Path(__file__).resolve().parents[1] / "data" / "uploads")
    enable_hybrid_rag: bool = False
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = "qwen-plus"
    vision_api_key: str = ""
    vision_base_url: str = ""
    vision_model: str = ""
    ai_request_timeout_seconds: float = 300
    cors_origins: str = "*"

    @field_validator("kb_db_path", "chroma_dir", "upload_dir", mode="after")
    @classmethod
    def resolve_project_path(cls, value: str) -> str:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return str(path.resolve())

    @field_validator("database_url", mode="after")
    @classmethod
    def resolve_sqlite_url(cls, value: str) -> str:
        prefix = "sqlite:///"
        if not value.startswith(prefix):
            return value
        raw_path = value.removeprefix(prefix)
        if raw_path == ":memory:":
            return value
        path = Path(raw_path).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return f"{prefix}{path.resolve().as_posix()}"

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def resolved_vision_api_key(self) -> str:
        return self.vision_api_key or self.llm_api_key

    @property
    def resolved_vision_base_url(self) -> str:
        return self.vision_base_url or self.llm_base_url

    @property
    def resolved_vision_model(self) -> str:
        return self.vision_model or self.llm_model


settings = Settings()
