from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from sqlalchemy import URL
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = Field(default="postgres", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(default="tech_companies", alias="POSTGRES_DB")
    postgres_user: str = Field(default="tech_user", alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(alias="POSTGRES_PASSWORD")
    import_storage_dir: Path = Field(
        default=Path("/app/storage/imports"),
        alias="IMPORT_STORAGE_DIR",
    )
    kestra_import_webhook_url: str | None = Field(
        default=None,
        alias="KESTRA_IMPORT_WEBHOOK_URL",
    )
    internal_api_token: SecretStr | None = Field(
        default=None,
        alias="INTERNAL_API_TOKEN",
    )

    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    @field_validator("kestra_import_webhook_url", mode="before")
    @classmethod
    def empty_webhook_url_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @field_validator("internal_api_token", mode="before")
    @classmethod
    def empty_internal_api_token_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None

    @property
    def database_connection_url(self) -> str | URL:
        if self.database_url:
            return self.database_url

        return URL.create(
            drivername="postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
