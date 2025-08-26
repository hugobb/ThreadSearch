
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from models import api as models_api
from stores import api as stores_api
from jobs import api as jobs_api
from jobs.core import QUEUE, clients, JOBS, restore_incomplete_jobs
from jobs import worker

_worker_task: asyncio.Task | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _worker_task

    # 🔑 Requeue interrupted jobs before worker starts
    await restore_incomplete_jobs(QUEUE)

    # Start worker
    _worker_task = asyncio.create_task(worker())
    yield

    # Shutdown worker
    if _worker_task:
        _worker_task.cancel()
        try:
            await _worker_task
        except asyncio.CancelledError:
            pass



app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(models_api.router)
app.include_router(stores_api.router)
app.include_router(jobs_api.router)


@app.websocket("/ws/jobs")
async def jobs_ws(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    # send initial snapshot
    for job in JOBS.values():
        await ws.send_json({"type": "job_update", "job": job.dict()})
    try:
        while True:
            await ws.receive_text()  # keep alive
    except WebSocketDisconnect:
        clients.discard(ws)