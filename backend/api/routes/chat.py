from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.auth import get_current_user
from worker.db.models import User, Conversation, Message, Approval
from worker.db.session import get_session
from worker.db.models import ModelSettings
from services.chat import start_chat_task

router = APIRouter(tags=['chat'])


class ChatIn(BaseModel):
    text: str
    conversation_id: str | None = None


class ChatOut(BaseModel):
    task_id: str
    conversation_id: str

class ConversationIn(BaseModel):
    title: str = ""

class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str

class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    created_at: datetime

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

    task = await start_chat_task(session, user, conversation.id, body.text)
    return ChatOut(task_id=task.task_id, conversation_id=conversation.id)

@router.get("/conversations", response_model=List[ConversationOut])
async def list_conversations(user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    )
    return rows.all()

@router.get("/conversations/{converstation_id}/messages", response_model=List[MessageOut])
async def get_message(conversation_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status_code=400, detail="Conversation not found")

    rows = await session.scalars(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at))

    return rows.all()

@router.post("/conversations", response_model=ConversationOut, status_code=201)
async def create_conversation(body: ConversationIn, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    conversation = Conversation(user_id=user.id, title=body.title[:200])
    session.add(conversation)

    await session.commit()

    return conversation

@router.get("/conversations/{conversation_id}/approvals/pending")
async def pending_approvals(conversation_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    rows = await session.scalars(select(Approval).where(Approval.conversation_id == conversation_id, Approval.user_id == user.id, Approval.status == "pending"))

    return [{"id": a.id, "payload": a.payload, "created_at": a.created_at} for a in rows]