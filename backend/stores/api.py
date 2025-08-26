import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile
from fastapi.params import Form
from pydantic import BaseModel
from pathlib import Path

from config import STORES_DIR
from jobs.core import Job, JOBS, QUEUE

from .core import Store, get_store, list_stores


# -----------------------------
# Schemas
# -----------------------------
class CreateStoreReq(BaseModel):
    name: str
    model: str


class AddTextReq(BaseModel):
    store: str
    text: str


class AddTextsReq(BaseModel):
    store: str
    texts: List[str]
    batch_size: Optional[int] = 64


class DeleteTextReq(BaseModel):
    store: str
    id: str


class SearchReq(BaseModel):
    store: str
    query: str
    k: int = 5


# -----------------------------
# Router
# -----------------------------
router = APIRouter()


@router.get("/stores/list")
def stores_list():
    return {"stores": list_stores()}


@router.post("/stores/create")
def create_store(req: CreateStoreReq):
    Store.create(req.name, STORES_DIR, req.model)
    return {"ok": True, "name": req.name, "model": req.model}


@router.get("/stores/info/{name}")
def store_info(name: str):
    s = get_store(name)
    return {"name": name, "model": s.meta["model"], "count": s.count}


@router.post("/stores/add_text")
def store_add_text(req: AddTextReq):
    s = get_store(req.store)
    entry = s.add_text(req.text)
    return {"ok": True, "entry": entry}


@router.post("/stores/add_texts")
def store_add_texts(req: AddTextsReq):
    s = get_store(req.store)
    entries = s.add_texts(req.texts, batch_size=req.batch_size or 64)
    return {"ok": True, "entries": entries}


@router.get("/stores/{name}/entries")
def store_entries(name: str):
    s = get_store(name)
    return {"entries": s.get_all()}


@router.post("/stores/delete_text")
def store_delete(req: DeleteTextReq):
    s = get_store(req.store)
    ok = s.delete(req.id)
    return {"ok": ok}


# 🔑 Delete an entire store
@router.post("/stores/delete/{name}")
def delete_store(name: str):
    s = get_store(name)
    s.delete_all()
    return {"ok": True}


# 🔑 Upload file as background job, now with batch_size
@router.post("/stores/upload_file")
async def upload_file(
    store: str = Form(...),
    file: UploadFile = None,
    batch_size: int = Form(64),
):
    tmp_path = Path(f"/tmp/{uuid.uuid4()}_{file.filename}")
    with open(tmp_path, "wb") as f:
        f.write(await file.read())

    # create job with batch_size
    job = Job(store, file.filename, tmp_path, batch_size=batch_size)
    JOBS[job.id] = job
    await QUEUE.put(job)

    return {"job_id": job.id}


# 🔑 New POST /search endpoint
@router.post("/search")
def search(req: SearchReq):
    s = get_store(req.store)
    results = s.search(req.query, req.k)
    return {"results": results}
