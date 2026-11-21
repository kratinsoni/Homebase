from pathlib import Path
from typing import List

from langchain_core.messages import AIMessageChunk, AIMessage, ToolMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.types import Command
from taskiq import Context, TaskiqDepends, TaskiqEvents, TaskiqState
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from worker.agent.graph import build_graph
from worker.config.settings import settings
from worker.events import EventPublisher
from worker.llm.chat_model import build_chat_model
from worker.tools.mcp.manager import DEFAULT_SERVERS, MCPManager
import aiosqlite
from worker.llm.profiles import get_model_profile
from worker.db.session import SessionLocal
from worker.db.models import Message, Approval
from redis.asyncio import Redis

broker = RedisStreamBroker(settings.redis_url).with_result_backend(RedisAsyncResultBackend(redis_url=settings.redis_url))

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState):
    state.redis = Redis.from_url(settings.redis_url, decode_responses=True)

    if settings.database_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        state.pool = AsyncConnectionPool(
            settings.database_url,
            max_size=10,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row},
        )

        await state.pool.open()
        state.checkpointer = AsyncPostgresSaver(state.pool)
        await state.checkpointer.setup()
        state.close_db = state.pool.close
    else:
        # SQLite (your Windows PC)
        data_dir = Path(settings.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(data_dir / "checkpoints.db")
        state.checkpointer = AsyncSqliteSaver(db)
        state.close_db = db.close

async def execute_graph(user_id: str, conversation_id: str, graph_input, context: Context = TaskiqDepends()) -> str:
    events = EventPublisher(conversation_id, context.state.redis, task_id=context.message.task_id)
    await events.emit("status", state="running")
    profile = await get_model_profile(user_id)
    model = build_chat_model(profile)
    tools = MCPManager(DEFAULT_SERVERS)
    try:
        await tools.start()
        app = build_graph(model, tools, checkpointer=context.state.checkpointer)

        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": settings.recursion_limit,
        }

        async for chunk in app.astream(graph_input, config, stream_mode=["messages", "updates"], version="v2"):
            if chunk["type"] == "messages":
                message, metadata = chunk["data"]

                if metadata.get("langgraph_node") == "agent" and isinstance(message, AIMessageChunk):
                    text = message.text
                    if text:
                        await events.emit("token", text=text)
            elif chunk["type"] == "updates":
                for node, update in chunk["data"].items():
                    print("UPDATE from node:", node, flush=True)
                    if not isinstance(update, dict):
                        continue  # for example "__interrupt__": a tuple of Interrupt objects
                    for msg in update.get("messages", []):
                        if isinstance(msg, AIMessage):
                            for call in msg.tool_calls:
                                await events.emit("tool_call", name=call["name"], arguments=call["args"])
                        elif isinstance(msg, ToolMessage):
                            await events.emit("tool_result", name=msg.name, preview=str(msg.content)[:200])

        state = await app.aget_state(config)

        interrupts = [i for task in state.tasks for i in task.interrupts]
        if interrupts:
            payload = interrupts[0].value

            async with SessionLocal() as session:
                approval = Approval(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    task_id=context.message.task_id,
                    payload=payload
                )

                session.add(approval)
                await session.commit()
            await events.emit("approval_required", approval_id=approval.id, **payload)
            await events.emit("done", state="waiting_approval")
            return ""

        reply = state.values["messages"][-1].text or ""

        async with SessionLocal() as session:
            session.add(Message(
                conversation_id=conversation_id,
                role="assistant",
                task_id=context.message.task_id,
                content=reply,
            ))
            await session.commit()

        await events.emit("message", content=reply)
        await events.emit("done", state="completed")
        return reply

    except Exception as e:
        await events.emit("error", content=str(e))
        await events.emit("done", state="failed")
        raise

    finally:
        await tools.close()

@broker.task
async def run_agent(user_id: str, conversation_id: str, text: str, context: Context = TaskiqDepends()) -> str:
    return await execute_graph(
        user_id, conversation_id, {"messages": [{"role": "user", "content": text}]}, context
    )


@broker.task
async def resume_agent(user_id: str, conversation_id: str, approved: bool, context: Context = TaskiqDepends()) -> str:
    return await execute_graph(
        user_id, conversation_id, Command(resume={"approved": approved}), context
    )

@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown(state: TaskiqState):
    await state.close_db()
    await state.redis.aclose()