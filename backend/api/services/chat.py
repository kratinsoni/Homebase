from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from worker.db.models import User, ModelSettings, TaskRecord, Message, Approval
from worker.jobqueue.tasks import run_agent


async def start_chat_task(session: AsyncSession, user: User, conversation_id: str, text: str) -> str:
    has_settings = await session.scalar(
        select(ModelSettings.id).where(ModelSettings.user_id == user.id)
    )
    if has_settings is None:
        raise HTTPException(400, "Add your API key in the model settings first.")

    pending = await session.scalar(
        select(Approval.id).where(
            Approval.conversation_id == conversation_id,
            Approval.status == "pending",
        )
    )
    if pending:
        raise HTTPException(409, "Answer the pending approval first.")

    session.add(Message(conversation_id=conversation_id, role="user", content=text))
    await session.commit()

    task = await run_agent.kiq(user_id=user.id, conversation_id=conversation_id, text=text)
    session.add(TaskRecord(id=task.task_id, user_id=user.id, conversation_id=conversation_id))
    await session.commit()
    return task.task_id