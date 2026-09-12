"""Construct the configured LLM implementation without making network calls."""

from app.core.config import Settings
from app.llm.base import LLMClient
from app.llm.deepseek import DeepSeekLLMClient
from app.llm.fake import FakeLLMClient


def create_llm_client(settings: Settings) -> LLMClient:
    if settings.llm_backend == "fake":
        return FakeLLMClient()

    return DeepSeekLLMClient(
        base_url=str(settings.deepseek_base_url),
        api_key=settings.deepseek_api_key,
        model=settings.deepseek_model,
        thinking_enabled=settings.deepseek_thinking_enabled,
        timeout_seconds=settings.deepseek_timeout_seconds,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
    )
