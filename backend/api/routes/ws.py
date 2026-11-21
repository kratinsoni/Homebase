import asyncio
import json
import time

import jwt
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from services.approvals import decide_approval
from services.auth import ALGORITHM
from services.chat import start_chat_task
from worker.config.settings import settings
from worker.db.models import Conversation, User
from worker.db.session import SessionLocal
from worker.events import conversation_stream_key

router = APIRouter(tags=["websocket"])


async def authenticate(ws: WebSocket) -> User | None:
    try:
        msg = await asyncio.wait_for(ws.receive_json(), timeout=10)
    except (asyncio.TimeoutError, WebSocketDisconnect, ValueError):
        return None
    if msg.get("type") != "auth":
        return None
    try:
        payload = jwt.decode(msg.get("token", ""), settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    async with SessionLocal() as session:
        return await session.get(User, payload.get("sub"))


@router.websocket("/ws/conversations/{conversation_id}")
async def conversation_ws(ws: WebSocket, conversation_id: str):
    await ws.accept()

    user = await authenticate(ws)
    if user is None:
        await ws.close(code=4401, reason="Unauthorized")
        return

    async with SessionLocal() as session:
        conversation = await session.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        await ws.close(code=4404, reason="Conversation not found")
        return

    send_lock = asyncio.Lock()

    async def send(obj: dict):
        async with send_lock:
            await ws.send_json(obj)

    await send({"type": "ready"})

    redis = ws.app.state.redis
    key = conversation_stream_key(conversation_id)

    async def forward_events():
        last_id = f"{int(time.time() * 1000)}-0"  # only events from now on
        while True:
            result = await redis.xread({key: last_id}, block=15_000, count=100)
            for _stream, entries in result or []:
                for event_id, fields in entries:
                    last_id = event_id
                    await send({"id": event_id, "type": fields["type"], **json.loads(fields["data"])})

    async def receive_commands():
        while True:
            msg = await ws.receive_json()
            if msg.get("type") == "message":
                text = (msg.get("text") or "").strip()
                if not text:
                    continue
                async with SessionLocal() as session:
                    try:
                        task_id = await start_chat_task(session, user, conversation_id, text)
                    except HTTPException as e:
                        await send({"type": "error", "message": e.detail})
                        continue
                await send({"type": "accepted", "task_id": task_id})
            elif msg.get("type") == "approval":
                async with SessionLocal() as session:
                    try:
                        task_id = await decide_approval(session, user, conversation_id, msg.get("approval_id", ""), bool(msg.get("approved")))
                    except HTTPException as e:
                        await send({"type": "error", "message": e.detail})
                        continue
                await send({"type": "accepted", "task_id": task_id})
            else:
                await send({"type": "error", "message": f"Unknown message type: {msg.get('type')}"})

    forward = asyncio.create_task(forward_events())
    try:
        await receive_commands()
    except WebSocketDisconnect:
        pass
    finally:
        forward.cancel()