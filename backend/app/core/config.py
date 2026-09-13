"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import AnyHttpUrl, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'data' / 'legalmind.db').as_posix()}"
DEFAULT_CHROMA_PERSIST_DIRECTORY = BACKEND_DIR / "data" / "chroma"


class Settings(BaseSettings):
    """Validated settings loaded from environment variables and a local .env."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="LEGALMIND_",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    app_name: str = "LegalMind API"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    cors_origins: tuple[str, ...] = ("http://localhost:5173",)

    database_url: SecretStr = SecretStr(DEFAULT_DATABASE_URL)
    postgres_smoke_url: SecretStr | None = None
    redis_url: SecretStr = SecretStr("redis://127.0.0.1:6379/0")
    chroma_persist_directory: Path = DEFAULT_CHROMA_PERSIST_DIRECTORY
    jwt_secret_key: SecretStr | None = None
    jwt_issuer: str = "legalmind-api"
    jwt_audience: str = "legalmind-web"
    access_token_expire_minutes: int = Field(default=60, ge=5, le=1440)

    llm_backend: Literal["deepseek", "fake"] = "fake"
    deepseek_base_url: AnyHttpUrl = AnyHttpUrl("https://api.deepseek.com")
    deepseek_api_key: SecretStr | None = None
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_thinking_enabled: bool = False
    deepseek_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    llm_temperature: float = Field(default=0.2, ge=0, le=2)
    llm_max_tokens: int = Field(default=2048, ge=1, le=32768)

    @field_validator("cors_origins")
    @classmethod
    def normalize_origins(cls, origins: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(
            origin.strip().rstrip("/") for origin in origins if origin.strip()
        )
        if not normalized:
            raise ValueError("At least one CORS origin must be configured")
        if len(set(normalized)) != len(normalized):
            raise ValueError("CORS origins must be unique")
        for origin in normalized:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.hostname
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path
                or parsed.query
                or parsed.fragment
            ):
                raise ValueError("CORS origins must be bare HTTP(S) origins")
        return normalized

    @field_validator("deepseek_model")
    @classmethod
    def validate_model_name(cls, model: str) -> str:
        normalized = model.strip()
        if not normalized:
            raise ValueError("DeepSeek model name cannot be empty")
        return normalized

    @field_validator("deepseek_api_key", mode="before")
    @classmethod
    def normalize_empty_api_key(cls, api_key: object) -> object:
        if isinstance(api_key, str) and not api_key.strip():
            return None
        if isinstance(api_key, SecretStr) and not api_key.get_secret_value().strip():
            return None
        return api_key

    @field_validator("postgres_smoke_url", mode="before")
    @classmethod
    def normalize_empty_postgres_smoke_url(cls, url: object) -> object:
        if isinstance(url, str) and not url.strip():
            return None
        if isinstance(url, SecretStr) and not url.get_secret_value().strip():
            return None
        return url

    @field_validator("chroma_persist_directory")
    @classmethod
    def resolve_chroma_persist_directory(cls, path: Path) -> Path:
        if path.is_absolute():
            return path
        return (BACKEND_DIR / path).resolve()

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def normalize_empty_jwt_secret(cls, secret: object) -> object:
        if isinstance(secret, str) and not secret.strip():
            return None
        if isinstance(secret, SecretStr) and not secret.get_secret_value().strip():
            return None
        return secret

    @field_validator("jwt_issuer", "jwt_audience")
    @classmethod
    def validate_jwt_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("JWT issuer and audience cannot be empty")
        return normalized

    @model_validator(mode="after")
    def validate_environment_safety(self) -> "Settings":
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS origins are not allowed with credentials")
        if self.environment == "production" and self.debug:
            raise ValueError("Debug mode cannot be enabled in production")
        if self.environment == "production":
            if self.jwt_secret_key is None:
                raise ValueError("JWT secret must be configured in production")
            if len(self.jwt_secret_key.get_secret_value()) < 32:
                raise ValueError("JWT secret must contain at least 32 characters")
        if self.llm_backend == "deepseek":
            if self.deepseek_base_url.scheme != "https":
                raise ValueError("DeepSeek requires an HTTPS base URL")
            if (
                self.deepseek_base_url.username is not None
                or self.deepseek_base_url.password is not None
                or self.deepseek_base_url.query is not None
                or self.deepseek_base_url.fragment is not None
            ):
                raise ValueError("DeepSeek base URL cannot contain credentials or parameters")
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable configuration instance."""

    return Settings()
