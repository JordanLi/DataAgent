"""DeepSeek LLM provider implementation (compatible with OpenAI client)."""

from collections.abc import AsyncGenerator

from openai import AsyncOpenAI

from app.config import get_settings
from app.core.llm.base import BaseLLM


class DeepSeekLLM(BaseLLM):
    """DeepSeek API uses OpenAI-compatible protocol."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url or "https://api.deepseek.com/v1",
        )
        self.model = settings.llm_model

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=False,
        )
        return response.choices[0].message.content or ""

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> AsyncGenerator[str, None]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
