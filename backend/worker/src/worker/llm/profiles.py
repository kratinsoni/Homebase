from worker.config.settings import ModelProfile
from worker.db.models import ModelSettings
from sqlalchemy import select
from worker.db.session import SessionLocal
from worker.encrytion import decrypt


class MissingModelSettings(Exception):
    pass

async def get_model_profile(user_id: str) -> ModelProfile:
    async with SessionLocal() as session:
        row = await session.scalar(select(ModelSettings).where(ModelSettings.user_id == user_id))

    if row is None:
        raise MissingModelSettings("No API KEY SAVED")
    return ModelProfile(
        provider=row.provider,
        model=row.model,
        api_key=decrypt(row.key_ciphertext),
        base_url=row.base_url,
    )