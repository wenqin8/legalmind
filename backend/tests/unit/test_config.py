import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_load_without_deepseek_key() -> None:
    settings = Settings(_env_file=None, llm_backend="deepseek")

    assert settings.llm_backend == "deepseek"
    assert settings.deepseek_api_key is None


def test_empty_deepseek_key_is_treated_as_missing(monkeypatch) -> None:
    monkeypatch.setenv("LEGALMIND_DEEPSEEK_API_KEY", "   ")

    settings = Settings(_env_file=None, llm_backend="deepseek")

    assert settings.deepseek_api_key is None


def test_environment_variables_override_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LEGALMIND_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LEGALMIND_LLM_MAX_TOKENS", "1024")
    monkeypatch.setenv(
        "LEGALMIND_CORS_ORIGINS", '["http://localhost:5173","http://127.0.0.1:5173"]'
    )

    settings = Settings(_env_file=None)

    assert settings.log_level == "WARNING"
    assert settings.llm_max_tokens == 1024
    assert settings.cors_origins == (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )


def test_secret_is_masked_in_repr_and_serialization() -> None:
    secret = "never-print-this-key"
    settings = Settings(_env_file=None, deepseek_api_key=secret)

    assert secret not in repr(settings)
    assert secret not in settings.model_dump_json()


def test_settings_are_immutable() -> None:
    settings = Settings(_env_file=None)

    with pytest.raises(ValidationError):
        settings.log_level = "ERROR"

    assert isinstance(settings.cors_origins, tuple)
    with pytest.raises(TypeError):
        settings.cors_origins[0] = "https://untrusted.example"


@pytest.mark.parametrize(
    "overrides",
    [
        {"environment": "production", "debug": True},
        {"cors_origins": ["*"]},
        {"cors_origins": []},
        {"cors_origins": ["http://localhost:5173", "http://localhost:5173/"]},
        {"cors_origins": ["null"]},
        {"cors_origins": ["http://localhost:5173/not-an-origin"]},
        {
            "llm_backend": "deepseek",
            "deepseek_base_url": "http://api.deepseek.com",
        },
    ],
)
def test_unsafe_settings_are_rejected(overrides: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)
