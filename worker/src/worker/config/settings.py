import os
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import BaseModel

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[4]

load_dotenv(BACKEND_DIR / ".env")

class ModelProfile(BaseModel):
    provider: str
    model: str
    api_key: str = field(default="", repr=False)  # repr=False: the key is not printed
    base_url: str | None = None


class Settings(BaseModel):
    default_model: ModelProfile
    redis_url: str
    workspace_dir: str
    recursion_limit: int
    data_dir: str
    database_url: str
    jwt_secret: str
    jwt_expires_minutes: int
    encryption_key: str


settings = Settings(
    default_model=ModelProfile(
        provider=os.getenv("MODEL_PROVIDER", "gemini"),
        model=os.getenv("MODEL_NAME", "gemini-3-flash-preview"),
        api_key=os.getenv("MODEL_API_KEY", ""),
        base_url=os.getenv("MODEL_BASE_URL") or None,
    ),
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    workspace_dir=os.getenv("WORKSPACE_DIR", "D:/Homebase/workspace"),
    recursion_limit=int(os.getenv("RECURSION_LIMIT", "12")),
    data_dir=os.getenv("DATA_DIR", str(BACKEND_DIR / "data")),
    database_url=os.getenv("DATABASE_URL", ""),
    jwt_secret=os.getenv("JWT_SECRET", ""),
    jwt_expires_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60")),
    encryption_key=os.getenv("ENCRYPTION_KEY", "")
)