from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import get_current_user
from worker.db.models import ModelSettings, User, utc_now
from worker.db.session import get_session
from worker.encrytion import encrypt
from worker.llm.providers import PROVIDERS

router = APIRouter(prefix="/me/model", tags=["models"])

class ModelSettingsIn(BaseModel):
    provider: str
    model: str
    api_key: str = Field(..., min_length=10)


class ModelSettingsOut(BaseModel):
    provider: str
    model: str
    api_key: str # masked

def to_out(row: ModelSettings) -> ModelSettingsOut:
    return ModelSettingsOut(
        provider=row.provider,
        model=row.model,
        api_key=f"••••{row.key_last4}"
    )

async def find_settings(session: AsyncSession, user_id: str) -> ModelSettings | None:
    return await session.scalar(select(ModelSettings).where(ModelSettings.user_id == user_id))

@router.get("", response_model=ModelSettingsOut)
async def get_model_settings(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    row = await find_settings(session, user.id)
    if row is None:
        raise HTTPException(status_code=404, detail="No Model Settings Yet, Add your API Key")
    return to_out(row)

@router.put("", response_model=ModelSettingsOut)
async def save_model_settings(body: ModelSettingsIn, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    spec = PROVIDERS.get(body.provider)
    if spec is None:
        allowed = [p for p, s in PROVIDERS.items()]
        raise HTTPException(422, f"Use one of these providers: {allowed}")

    row = await find_settings(session, user.id)
    if row is None:
        row = ModelSettings(user_id=user.id)
        session.add(row)

    row.provider = body.provider
    row.model = body.model
    row.key_ciphertext = encrypt(body.api_key)
    row.key_last4 = body.api_key[-4:]
    row.updated_at = utc_now()
    await session.commit()
    return to_out(row)

@router.delete("", status_code=204)
async def delete_model_settings(user_id: str, session: AsyncSession = Depends(get_session)):
    row = await find_settings(session, user_id)
    if row is None:
        raise HTTPException(422, f"Use one of these providers: {PROVIDERS}")

    await session.delete(row)
    await session.commit()
