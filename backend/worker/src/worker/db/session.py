from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from worker.config.settings import settings
from worker.db.models import Base

def _db_url() -> str:
    if settings.database_url:
        return settings.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite+aiosqlite:///{(data_dir / 'app.db').as_posix()}"

engine = create_async_engine(_db_url())

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session():
    async with SessionLocal() as session:
        yield session