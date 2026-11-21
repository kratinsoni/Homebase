from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from worker.db.models import User, Approval, TaskRecord, utc_now
from worker.jobqueue.tasks import resume_agent


async def decide_approval(
    session: AsyncSession, user: User, conversation_id: str, approval_id: str, approved: bool
) -> str:
    result = await session.execute(
        update(Approval)
        .where(
            Approval.id == approval_id,
            Approval.user_id == user.id,
            Approval.conversation_id == conversation_id,
            Approval.status == "pending",
        )
        .values(status="approved" if approved else "rejected", decided_at=utc_now())
    )
    if result.rowcount == 0:
        raise HTTPException(409, "Approval not found, or already answered.")
    await session.commit()

    task = await resume_agent.kiq(user_id=user.id, conversation_id=conversation_id, approved=approved)
    session.add(TaskRecord(id=task.task_id, user_id=user.id, conversation_id=conversation_id))
    await session.commit()
    return task.task_id