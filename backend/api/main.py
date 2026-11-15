from fastapi import FastAPI
from starlette.responses import HTMLResponse

from worker.jobqueue.tasks import run_agent, broker
from pydantic import BaseModel # type: ignore
from contextlib import asynccontextmanager

from worker.db.session import create_tables
from routes_auth import router as auth_router
from routes.chat import router as chat_router
from routes.tasks import router as task_router
from routes.model_settings import router as model_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.startup()    # ① runs one time, when the API starts
    yield                     # ② the API runs here and serves all requests
    await broker.shutdown()   # ③ runs one time, when the API stops (Ctrl+C)

app = FastAPI(title="Homebase API", lifespan=lifespan)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(task_router)
app.include_router(model_router)

@app.get("/", response_class=HTMLResponse)
async def health_check():
    return HTMLResponse(status_code=200, content="The Server is Running")