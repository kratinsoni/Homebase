from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException,  Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from services.auth import get_current_user
from worker.db.models import User, TaskRecord
from worker.db.session import get_session
from worker.jobqueue.tasks import broker

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    created_at: datetime


@router.get("/{task_id}")
async def get_task(task_id: str, user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    record = await session.get(TaskRecord, task_id)
    if record is None or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Task not found")

    backend = broker.result_backend
    if not await backend.is_result_ready(task_id):
        return {"task_id": task_id, "status": "pending"}
    result = await backend.get_result(task_id)

    if result.is_err:
        raise {"task_id": task_id, "status": "failed", "err": str(result.error)}

    return {"task_id": task_id, "status": "done", "reply": result.return_value}


@router.get("", response_model=List[TaskOut])
async def list_tasks(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.scalars(
        select(TaskRecord)
        .where(TaskRecord.user_id == user.id)
        .order_by(TaskRecord.created_at.desc())
        .limit(50)
    )
    return rows.all()




