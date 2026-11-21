from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from worker.config.settings import ModelProfile
from worker.llm.providers import PROVIDERS


def build_chat_model(profile: ModelProfile) -> BaseChatModel:
    spec = PROVIDERS.get(profile.provider)
    if spec is None:
        raise ValueError(f"Unknown provider '{profile.provider}'")

    kwargs = {
        "model": profile.model,
        "model_provider": spec.chat_provider,
        "api_key": profile.api_key,
        "timeout": 120,
        "max_retries": 3,
    }
    if spec.base_url:
        kwargs["base_url"] = spec.base_url
    return init_chat_model(**kwargs)