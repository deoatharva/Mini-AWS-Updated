from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/app/config.py -> repo root
BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_SECRET_KEY = "development-only-change-me"


def _default_database_url() -> str:
    """Keep the metadata database inside data/ regardless of the shell cwd."""
    return f"sqlite:///{(BASE_DIR / 'data' / 'mini_aws.db').as_posix()}"


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = DEFAULT_SECRET_KEY
    database_url: str = _default_database_url()
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://127.0.0.1:5173,http://localhost:5173"
    session_ttl_hours: int = Field(default=24, ge=1, le=24 * 30)
    data_dir: Path = BASE_DIR / "data"
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, ge=1)
    compute_port_start: int = Field(default=18000, ge=1024, le=65535)
    compute_port_end: int = Field(default=18999, ge=1024, le=65535)
    application_port_start: int = Field(default=19000, ge=1024, le=65535)
    application_port_end: int = Field(default=19999, ge=1024, le=65535)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def buckets_dir(self) -> Path:
        return self.data_dir / "buckets"

    @property
    def instances_dir(self) -> Path:
        return self.data_dir / "instances"

    @property
    def applications_dir(self) -> Path:
        return self.data_dir / "applications"

    @property
    def databases_dir(self) -> Path:
        return self.data_dir / "databases"

    def ensure_data_dirs(self) -> None:
        for path in (
            self.data_dir,
            self.buckets_dir,
            self.instances_dir,
            self.applications_dir,
            self.databases_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @model_validator(mode="after")
    def _require_secret_outside_development(self) -> "Settings":
        if self.app_env != "development" and self.secret_key == DEFAULT_SECRET_KEY:
            raise ValueError("SECRET_KEY must be set when APP_ENV is not 'development'.")
        return self

    @model_validator(mode="after")
    def _validate_compute_port_range(self) -> "Settings":
        if self.compute_port_start > self.compute_port_end:
            raise ValueError("COMPUTE_PORT_START must be less than or equal to COMPUTE_PORT_END.")
        return self

    @model_validator(mode="after")
    def _validate_application_port_range(self) -> "Settings":
        if self.application_port_start > self.application_port_end:
            raise ValueError(
                "APPLICATION_PORT_START must be less than or equal to APPLICATION_PORT_END."
            )
        return self


settings = Settings()
