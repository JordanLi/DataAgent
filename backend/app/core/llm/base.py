"""Base abstract class for all LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator


class BaseLLM(ABC):
    """Abstract base class that all LLM implementations must follow."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        """
        Send a non-streaming chat request.
        
        :param messages: List of dicts with 'role' ('system', 'user', 'assistant') and 'content'
        :param temperature: LLM generation temperature
        :return: Generated text
        """
        pass

    @abstractmethod
    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> AsyncGenerator[str, None]:
        """
        Send a streaming chat request.
        
        :param messages: List of dicts with 'role' and 'content'
        :param temperature: LLM generation temperature
        :return: Async generator of text chunks
        """
        pass
