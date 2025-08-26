import asyncio, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict
import uuid
from fastapi import WebSocket

JOBS_DIR = Path(".cache/jobs")
JOBS_DIR.mkdir(exist_ok=True)

JOBS = {}
QUEUE = asyncio.Queue()
clients: set[WebSocket] = set()


class Job:
    def __init__(self, store: str, filename: str, path: Path, batch_size: int, job_id: str | None = None):
        self.id = job_id or str(uuid.uuid4())
        self.store = store
        self.filename = filename
        self.path = path
        self.batch_size = batch_size
        self.status = "pending"
        self.progress = 0
        self.total = 0
        self.processed = 0
        self.error = None
        self.logs: list[str] = []
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def touch(self):
        self.updated_at = self._now()

    def log(self, message: str):
        ts = self._now()
        self.logs.append({"timestamp": ts, "message": message})
        self.touch()

    def dict(self):
        return {
            "id": self.id,
            "batch_size": self.batch_size,
            "store": self.store,
            "filename": self.filename,
            "status": self.status,
            "progress": self.progress,
            "processed": self.processed,
            "total": self.total,
            "error": self.error,
            "logs": self.logs,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "path": str(self.path),
        }

    # -----------------------
    # Persistence
    # -----------------------
    @property
    def file(self) -> Path:
        return JOBS_DIR / f"{self.id}.json"

    def save(self):
        self.updated_at = datetime.now().isoformat()
        with open(self.file, "w") as f:
            json.dump(self.dict(), f, indent=2)

    @classmethod
    def load(cls, file: Path):
        with open(file, "r") as f:
            data = json.load(f)
        print(data)
        print(data.get("store"))
        job = cls(
            store=data["store"],
            filename=data["filename"],
            path=Path(data["path"]),
            batch_size=data["batch_size"],
            job_id=data["id"],
        )
        job.status = data["status"]
        job.progress = data["progress"]
        job.total = data["total"]
        job.processed = data["processed"]
        job.error = data["error"]
        job.logs = data["logs"]
        job.created_at = data["created_at"]
        job.updated_at = data["updated_at"]
        return job

def list_jobs() -> Dict[str, Job]:
    """
    Load all jobs from disk into JOBS dict.
    """
    global JOBS
    JOBS = {}
    for file in JOBS_DIR.glob("*.json"):
        try:
            job = Job.load(file)
            JOBS[job.id] = job
        except Exception as e:
            print(f"[jobs] Failed to load job from {file}: {e}")
    return JOBS


async def restore_incomplete_jobs(queue: asyncio.Queue):
    """
    On startup, requeue any jobs that were 'processing' or 'pending'
    when the server stopped.
    """
    jobs = list_jobs()
    for job in jobs.values():
        if job.status in ("processing", "pending"):
            print(f"[jobs] Requeuing interrupted job {job.id} ({job.status})")
            job.status = "pending"
            job.log("Job requeued after restart.")
            await queue.put(job)