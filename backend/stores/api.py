import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile
from fastapi.params import Form
import numpy as np
from pydantic import BaseModel
from pathlib import Path
import networkx as nx


from models.registry import get_model
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


class InterpolateReq(BaseModel):
    store: str
    sentence_a: str
    sentence_b: str
    steps: int = 5  # number of points to interpolate
    k: int = 1      # how many results per step

class BuildGraphReq(BaseModel):
    store: str
    k: int = 10
    efConstruction: int = 200
    M: int = 32

class GraphSearchReq(BaseModel):
    store: str
    start: str
    end: str
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


@router.post("/interpolate")
def interpolate(req: InterpolateReq):
    s = get_store(req.store)
    model_id = s.meta["model"]
    model = get_model(model_id)()
    model.load()

    # encode both endpoints
    v_a = model.embed([req.sentence_a]).astype(np.float32)[0]
    v_b = model.embed([req.sentence_b]).astype(np.float32)[0]

    results = []
    for i in range(1, req.steps + 1):
        t = i / (req.steps + 1)
        v_interp = (1 - t) * v_a + t * v_b
        v_interp = v_interp / np.linalg.norm(v_interp)  # normalize like search
        sims, ids = s.index.search(np.array([v_interp]), min(req.k, s.count))
        entries = s.get_all()
        step_results = [
            {
                "id": entries[int(idx)]["id"],
                "text": entries[int(idx)]["text"],
                "score": float(sim),
            }
            for idx, sim in zip(ids[0], sims[0])
        ]
        results.append({"step": i, "results": step_results})
    return {"interpolations": results}

@router.post("/stores/build_graph")
async def build_graph(req: BuildGraphReq):
    from jobs.core import Job, JOBS, QUEUE

    # Create background job
    job = Job(store=req.store, filename="graph", path=Path(""), batch_size=req.k)
    job.log("Queued graph build job")
    JOBS[job.id] = job
    await QUEUE.put(("build_graph", req.dict(), job.id))
    return {"job_id": job.id}


@router.post("/graph_search")
async def graph_search(req: GraphSearchReq):
    s = get_store(req.store)

    # 1) Get embeddings
    model_id = s.meta["model"]
    encoder = get_model(model_id)()
    encoder.load()
    v_start = encoder.embed([req.start]).astype(np.float32)
    v_end = encoder.embed([req.end]).astype(np.float32)

    G: nx.Graph
    # 2) Ensure graph exists
    print("Loading Grap...")
    if not hasattr(s, "graph") or s.graph is None:
        print("Graph not Found. Building graph...")
        G = await s.build_graph()

    else:
        G = s.graph

    print("Graph Loaded")

    # 3) Find closest nodes in the graph for start and end
    entries = s.get_all()
    embs = s.index.reconstruct_n(0, len(entries))
    dists_start = np.dot(embs, v_start.T).flatten()
    dists_end = np.dot(embs, v_end.T).flatten()
    start_node = int(np.argmax(dists_start))
    end_node = int(np.argmax(dists_end))

    # 4) Shortest path in the graph
    print("Computing Shortest Path...")
    path = nx.shortest_path(G, source=start_node, target=end_node, weight="weight")

    # 5) Optionally truncate or interpolate path to req.k
    if req.k and len(path) > req.k + 2:
        # keep start + end, subsample intermediate nodes
        step = max(1, len(path) // (req.k + 1))
        path = path[::step]
        if path[-1] != end_node:
            path.append(end_node)

    nodes = [{"id": entries[i]["id"], "text": entries[i]["text"]} for i in path]
    return {"nodes": nodes, "distance": float(len(path))}