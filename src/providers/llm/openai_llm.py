from collections.abc import AsyncIterator

from openai import AsyncOpenAI

from ...core.interfaces import LlmProvider, Message


class OpenAiLlmProvider(LlmProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def stream_reply(self, messages: list[Message]) -> AsyncIterator[str]:
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.5,
            max_tokens=250,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
