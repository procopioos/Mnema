from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Mnema API"
    environment: str = "dev"

    database_url: str = "postgresql+asyncpg://mnema:mnema@localhost:5432/mnema"
    redis_url: str = "redis://localhost:6379/0"

    # Storage
    storage_dir: str = "data"
    max_upload_size_mb: int = 50
    allowed_extensions: set[str] = {"pdf", "docx", "txt", "md"}

    # Quotas (per-workspace defaults; NULL on a workspace means "use these")
    max_documents_per_workspace: int = 100
    max_storage_bytes_per_workspace: int = 1_073_741_824  # 1 GiB

    # Ingestion
    chunk_size: int = 800
    chunk_overlap: int = 120

    # Arq
    arq_queue_name: str = "mnema"

    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    auth_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @property
    def auth_token_expire_seconds(self) -> int:
        return self.auth_token_expire_minutes * 60

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
