from dataclasses import dataclass, field
from openai import AsyncOpenAI


@dataclass
class ModelConfig:
    base_url: str
    model: str
    api_key: str

class ModelAdapter:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.client = AsyncOpenAI(api_key=config.api_key, base_url=config.base_url)

    async def close(self):
        await self.client.close()

    async def chat(self, messages, tools=None):
        kwargs = {"model": self.config.model, "messages": messages}

        if tools:
            kwargs["tools"] = tools

        response = await self.client.chat.completions.create(**kwargs)

        return response.choices[0].message