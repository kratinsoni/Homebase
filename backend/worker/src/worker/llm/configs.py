from worker.config.settings import ModelProfile
from worker.llm.adapter import ModelConfig
from worker.llm.providers import PROVIDERS


def resolve(profile: ModelProfile) -> ModelConfig:
    spec = PROVIDERS.get(profile.provider)

    if profile.base_url:
        base_url = profile.base_url
    elif spec:
        base_url = spec.base_url
    else:
        raise ValueError(
            f"Unknown provider '{profile.provider}'. "
            f"Use one of {list(PROVIDERS)}, or set base_url for a custom provider."
        )

    key = profile.api_key

    return ModelConfig(base_url=base_url, model=profile.model, api_key=key)