from pydantic import BaseModel


class ProviderSpec(BaseModel):
    id: str                       # the name in your API and database ("gemini", ...)
    chat_provider: str            # the name for init_chat_model ("google_genai", ...)
    base_url: str | None = None   # only for OpenAI-compatible services
    needs_key: bool = True


PROVIDERS: dict[str, ProviderSpec] = {
    p.id: p
    for p in [
        ProviderSpec(id="openai", chat_provider="openai"),
        ProviderSpec(id="gemini", chat_provider="google_genai"),
        ProviderSpec(id="groq", chat_provider="groq"),
        ProviderSpec(id="openrouter", chat_provider="openai", base_url="https://openrouter.ai/api/v1"),
    ]
}