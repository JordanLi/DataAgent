"""Anthropic Claude LLM provider implementation."""

from collections.abc import AsyncGenerator

from anthropic import AsyncAnthropic

from app.config import get_settings
from app.core.llm.base import BaseLLM


class ClaudeLLM(BaseLLM):
    def __init__(self) -> None:
        settings = get_settings()
        self.client = AsyncAnthropic(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )
        self.model = settings.llm_model

    def _convert_messages(self, messages: list[dict[str, str]]) -> tuple[str, list[dict[str, str]]]:
        """Extract system prompt and convert to Anthropic format."""
        system_prompt = ""
        anthropic_messages = []
        for msg in messages:
            role = msg["role"]
            if role == "system":
                system_prompt = msg["content"]
            else:
                anthropic_messages.append({"role": role, "content": msg["content"]})
        return system_prompt, anthropic_messages

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> str:
        system_prompt, converted_messages = self._convert_messages(messages)
        response = await self.client.messages.create(
            model=self.model,
            messages=converted_messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens=4096,
        )
        return response.content[0].text

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> AsyncGenerator[str, None]:
        system_prompt, converted_messages = self._convert_messages(messages)
        async with self.client.messages.stream(
            model=self.model,
            messages=converted_messages,
            system=system_prompt,
            temperature=temperature,
            max_tokens=4096,
        ) as stream:
            async for chunk in stream.text_stream:
                yield chunk
