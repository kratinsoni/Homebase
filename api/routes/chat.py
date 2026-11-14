from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from auth import get_current_user
from worker.db.models import User, Conversation, TaskRecord
from worker.db.session import get_session
from worker.jobqueue.tasks import run_agent
from worker.db.models import ModelSettings

router = APIRouter(tags=['chat'])


class ChatIn(BaseModel):
    text: str
    conversation_id: str | None = None


class ChatOut(BaseModel):
    task_id: str
    conversation_id: str


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str

@router.post("/chat", response_model=ChatOut)
async def chat(body: ChatIn, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    has_settings = await session.scalar(
        select(ModelSettings.id).where(ModelSettings.user_id == user.id)
    )
    if has_settings is None:
        raise HTTPException(400, "Add your API key in the model settings first.")

    if body.conversation_id is not None:
        conversation = await session.get(Conversation, body.conversation_id)
        if conversation is None or conversation.user_id != user.id:
            raise HTTPException(status_code=400, detail="Conversation not found")
    else:
        conversation = Conversation(user_id=user.id, title=body.text)
        session.add(conversation)
        await session.flush()

    task = await run_agent.kiq(user_id=user.id, conversation_id=conversation.id, text=body.text)

    session.add(TaskRecord(id=task.task_id, user_id=user.id, conversation_id=conversation.id))
    await session.commit()

    return ChatOut(task_id=task.task_id, conversation_id=conversation.id)

@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return rows.all()