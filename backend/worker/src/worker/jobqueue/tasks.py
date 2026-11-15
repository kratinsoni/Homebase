from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from taskiq import Context, TaskiqDepends, TaskiqEvents, TaskiqState
from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from worker.agent.graph import build_graph
from worker.config.settings import settings
from worker.llm.adapter import ModelAdapter
from worker.llm.configs import resolve
from worker.tools.mcp.manager import DEFAULT_SERVERS, MCPManager
import aiosqlite
from worker.llm.profiles import get_mode_profile
from worker.db.session import SessionLocal
from worker.db.models import Message

broker = RedisStreamBroker(settings.redis_url).with_result_backend(RedisAsyncResultBackend(redis_url=settings.redis_url))

@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState):

    if settings.database_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from psycopg.rows import dict_row
        from psycopg_pool import AsyncConnectionPool

        state.pool = AsyncConnectionPool(
            settings.database_url,
            max_size=10,
            open=False,
            kwargs={"autocommit": "True", "prepare_threshold": 0, "row_factory": dict_row},
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
@broker.task
async def run_agent(user_id: str, conversation_id: str, text: str, context: Context = TaskiqDepends()) -> str:
    profile = await get_mode_profile(user_id)
    adapter = ModelAdapter(resolve(profile))
    tools = MCPManager(DEFAULT_SERVERS)
    try:
        await tools.start()
        app = build_graph(adapter, tools, checkpointer=context.state.checkpointer)

        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": settings.recursion_limit,
        }

        result = await app.ainvoke({"messages": [{"role": "user", "content": text}]}, config)
        reply = result["messages"][-1]["content"] or ""

        async with SessionLocal() as session:
            session.add(Message(
                conversation_id=conversation_id,
                role="assistant",
                task_id=context.message.task_id,
                content=reply,
            ))
            await session.commit()

        return result["messages"][-1].get("content") or ""
    finally:
        await tools.close()
        await adapter.close()

@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown(state: TaskiqState):
    await state.close_db()