"""Factory to instantiate the configured LLM provider."""

from typing import Any

from app.config import get_settings
from app.core.llm.base import BaseLLM
from app.core.llm.claude_llm import ClaudeLLM
from app.core.llm.deepseek_llm import DeepSeekLLM
from app.core.llm.openai_llm import OpenAILLM


def create_llm(settings: Any = None) -> BaseLLM:
    """Create an LLM instance based on configuration."""
    if settings is None:
        settings = get_settings()
        
    provider = settings.llm_provider.lower().strip()

    if provider == "openai":
        return OpenAILLM()
    elif provider in ("claude", "anthropic"):
        return ClaudeLLM()
    elif provider == "deepseek":
        return DeepSeekLLM()
    else:
        raise ValueError(f"Unsupported LLM provider configured: {provider}")

def get_llm() -> BaseLLM:
    """Alias for create_llm()."""
    return create_llm()

class LLMFactory:
    """Legacy factory class for backward compatibility."""
    
    @staticmethod
    def get_llm() -> BaseLLM:
        return create_llm()
