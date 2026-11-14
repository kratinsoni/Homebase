from pydantic import BaseModel


class ProviderSpec(BaseModel):
    id: str
    base_url: str

PROVIDERS: dict[str, ProviderSpec] = {
    p.id: p
    for p in [
        ProviderSpec(id="openai", base_url="https://api.openai.com/v1"),
        ProviderSpec(id="gemini", base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
        ProviderSpec(id="groq", base_url="https://api.groq.com/openai/v1"),
        ProviderSpec(id="openrouter", base_url="https://openrouter.ai/api/v1"),
    ]
}