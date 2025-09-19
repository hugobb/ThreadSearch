import asyncio
from pathlib import Path
import pickle
from typing import Dict, List, Optional, TypedDict
import json
import uuid
import faiss
import numpy as np

from jobs import broadcast
from jobs.core import Job
from config import CACHE_FOLDER, STORES_DIR
from models.registry import get_model


def list_stores() -> List[str]:
    return [p.name for p in STORES_DIR.iterdir() if p.is_dir()]

class MetaData(TypedDict):
    name: str
    model: str
    dim: Optional[int]

def l2norm(x: np.ndarray) -> np.ndarray:
    x = x.astype(np.float32, copy=False)
    n = np.linalg.norm(x, axis=1, keepdims=True)
    n = np.maximum(n, 1e-12)
    return x / n


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.meta = self.load_meta()
        self.entries_path = self.path / "entries.jsonl"
        self.index_path = self.path / "index.faiss"
        self.graph_path = self.path / "graph.faiss"
        self.index: Optional[faiss.Index] = self._load_index()
        # self.graph: Optional[faiss.Index] = self._load_graph()


    def load_meta(self) -> MetaData:
        meta_path = self.path / "meta.json"
        if not meta_path.exists():
            raise FileNotFoundError(f"Meta file not found: {meta_path}")
        with open(meta_path, "r") as f:
            return json.load(f)

    @staticmethod
    def create(name: str, root: Path, model_id: str):
        store_path = root / name
        store_path.mkdir(parents=True, exist_ok=True)
        meta = {"name": name, "model": model_id, "dim": None}
        with open(store_path / "meta.json", "w") as f:
            json.dump(meta, f, indent=2)
        return Store(store_path)

    # -----------------------------
    # Index handling
    # -----------------------------
    def _load_index(self) -> Optional[faiss.Index]:
        if self.index_path.exists():
            return faiss.read_index(str(self.index_path))
        return None

    def _save_index(self):
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))

    @property
    def count(self) -> int:
        return self.index.ntotal if self.index is not None else 0

    # -----------------------------
    # Entries
    # -----------------------------
    def _get_all(self) -> List[Dict]:
        if not self.entries_path.exists():
            return []
        with open(self.entries_path, "r", encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def _append_entries(self, entries: List[Dict]):
        # Append a batch of entries atomically-ish
        with open(self.entries_path, "a", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    async def add_texts(self, texts: List[str], batch_size: int = 64, job: Job = None) -> List[Dict]:
        """
        Incrementally add texts:
          - embed per batch (off-thread)
          - append entries.jsonl per batch
          - add to FAISS and write index per batch
          - update/broadcast job progress per batch

        When called in the background (job != None), we avoid accumulating all entries in RAM
        and return an empty list (progress is visible via the job tracker). For small sync calls,
        we still return the list of created entries.
        """
        if not texts:
            return []

        model_id = self.meta["model"]
        model = get_model(model_id)()
        # Load encoder in a worker thread (blocking)
        await asyncio.to_thread(model.load, CACHE_FOLDER)

        collect_results = job is None
        if collect_results:
            all_entries: List[Dict] = []

        total = len(texts)
        if job:
            job.total = total
            # IMPORTANT: do not assume job.processed starts at 0.
            # The worker can set job.processed from persisted state before calling us.
            job.log(f"Starting ingestion of {total} texts (batch={batch_size}).")
            await broadcast(job)

        for i in range(0, total, batch_size):
            chunk = texts[i : i + batch_size]

            # 1) Compute embeddings (off-thread)
            embs = await asyncio.to_thread(model.embed, chunk)
            embs = l2norm(embs.astype(np.float32))

            # 2) Create entries for THIS batch (ids + text)
            entries_batch = [{"id": str(uuid.uuid4()), "text": t} for t in chunk]

            # 3) Ensure index is initialized / dims consistent
            dim = int(embs.shape[1])
            if self.index is None:
                # create index on first batch
                self.index = faiss.IndexFlatIP(dim)
            else:
                if self.index.d != dim:
                    raise ValueError(f"Index dim {self.index.d} != embedding dim {dim}")

            # Set meta dim the first time
            if not self.meta.get("dim"):
                self.meta["dim"] = dim
                # Persist meta change (off-thread)
                await asyncio.to_thread(self._write_meta)

            # 4) Append entries to file (off-thread)
            await asyncio.to_thread(self._append_entries, entries_batch)

            # 5) Add vectors to index & persist index file (off-thread)
            await asyncio.to_thread(self.index.add, embs)
            await asyncio.to_thread(faiss.write_index, self.index, str(self.index_path))

            # 6) Track results if this is a small sync call
            if collect_results:
                if 'all_entries' not in locals():
                    all_entries = []  # type: ignore
                all_entries.extend(entries_batch)

            # 7) Update job progress & broadcast
            if job:
                job.processed += len(chunk)
                # progress computed against this call's total
                pct = int((job.processed / job.total) * 100) if job.total else 100
                job.progress = max(min(pct, 100), 0)
                job.log(f"Processed {job.processed}/{job.total}")
                await broadcast(job)

        if job:
            job.progress = 100
            job.log("Ingestion complete.")
            await broadcast(job)

        return all_entries if collect_results else []

    def _write_meta(self):
        with open(self.path / "meta.json", "w", encoding="utf-8") as f:
            json.dump(self.meta, f, indent=2)

    async def reconcile_index(self, batch_size: int = 64, job: Job = None):
        """
        Ensure the FAISS index and entries.jsonl are consistent.
        If entries tail exists beyond index.ntotal, (re-)embed and add only that tail.
        """
        all_entries = self._get_all()
        n_entries = len(all_entries)
        n_index = self.count

        if n_entries == n_index:
            return  # already consistent

        if n_entries < n_index:
            raise RuntimeError(
                f"Inconsistent store: index has {n_index} vectors but only {n_entries} entries. "
                "Manual repair required."
            )

        # There are entries not yet in the index → index the tail
        tail_texts = [e["text"] for e in all_entries[n_index:]]
        if not tail_texts:
            return

        model_id = self.meta["model"]
        model = get_model(model_id)()
        await asyncio.to_thread(model.load, CACHE_FOLDER)

        if job:
            job.log(f"Reconciling index: adding missing {len(tail_texts)} entries.")
            await broadcast(job)

        for i in range(0, len(tail_texts), batch_size):
            chunk = tail_texts[i : i + batch_size]
            embs = await asyncio.to_thread(model.embed, chunk)
            embs = l2norm(embs.astype(np.float32))

            dim = int(embs.shape[1])
            if self.index is None:
                self.index = faiss.IndexFlatIP(dim)
                if not self.meta.get("dim"):
                    self.meta["dim"] = dim
                    await asyncio.to_thread(self._write_meta)
            else:
                if self.index.d != dim:
                    raise ValueError(f"Index dim {self.index.d} != embedding dim {dim}")

            await asyncio.to_thread(self.index.add, embs)
            await asyncio.to_thread(faiss.write_index, self.index, str(self.index_path))

            if job:
                job.log(f"Reconciled {min(n_index + i + len(chunk), n_entries)}/{n_entries}")
                await broadcast(job)

    def add_text(self, text: str) -> Dict:
        # For small sync API usage; not used by the async worker path
        # NOTE: This wraps the async version for convenience
        import anyio
        return anyio.run(self.add_texts, [text])[0]

    def get_all(self) -> List[Dict]:
        return self._get_all()

    def delete(self, entry_id: str) -> bool:
        entries = self._get_all()
        new_entries = [e for e in entries if e["id"] != entry_id]
        if len(new_entries) == len(entries):
            return False  # nothing deleted

        model_id = self.meta["model"]
        model = get_model(model_id)()
        model.load(cache_dir=CACHE_FOLDER)
        texts = [e["text"] for e in new_entries]

        if texts:
            embs = model.embed(texts).astype(np.float32)
            embs = l2norm(embs)
            self.index = faiss.IndexFlatIP(embs.shape[1])
            self.index.add(embs)
        else:
            self.index = None

        self._save_index()

        with open(self.entries_path, "w", encoding="utf-8") as f:
            for e in new_entries:
                f.write(json.dumps(e) + "\n")

        return True

    def search(self, query: str, k: int = 5) -> List[Dict]:
        if self.index is None or self.count == 0:
            return []
        model_id = self.meta["model"]
        model = get_model(model_id)()
        model.load(cache_dir=CACHE_FOLDER)
        q_emb = model.embed([query]).astype(np.float32)
        q_emb = l2norm(q_emb)
        sims, ids = self.index.search(q_emb, min(k, self.count))
        entries = self._get_all()
        return [
            {"id": entries[int(idx)]["id"], "text": entries[int(idx)]["text"], "score": float(sim)}
            for idx, sim in zip(ids[0], sims[0])
        ]

    def delete_all(self):
        import shutil
        shutil.rmtree(self.path)

    # -----------------------------
    # k-NN Graph
    # -----------------------------
    def _load_graph(self) -> Optional[faiss.Index]:
        if self.graph_path.exists():
            return faiss.read_index(str(self.graph_path))
        return None

    async def build_graph(self, k: int = 10, efConstruction: int = 200, M: int = 32, job: Job = None):
        """
        Build approximate k-NN graph from embeddings using HNSW.
        """
        if self.index is None or self.count == 0:
            raise RuntimeError("No embeddings indexed yet")

        dim = self.index.d
        n = self.count

        # Initialize HNSW index
        print("Initialize HNSW index")
        hnsw = faiss.IndexHNSWFlat(dim, M)
        hnsw.hnsw.efConstruction = efConstruction

        # Export vectors from store's FAISS index
        print("Export vectors from FAISS index")
        xb = np.empty((n, dim), dtype=np.float32)
        self.index.reconstruct_n(0, n, xb)

        if job:
            job.total = n
            job.processed = 0
            job.log(f"Building k-NN graph with N={n}, M={M}, efC={efConstruction}")
            await broadcast(job)

        # Add vectors in chunks so we can track progress
        print("Adding vectors")
        batch_size = 4
        for i in range(0, n, batch_size):
            chunk = xb[i : i + batch_size]
            hnsw.add(chunk)
            if job:
                job.processed = min(i + len(chunk), n)
                job.progress = int(job.processed / job.total * 100)
                job.log(f"Inserted {job.processed}/{n} vectors into graph")
                await broadcast(job)

        print("Write index")
        faiss.write_index(hnsw, str(self.graph_path))
        self.graph = hnsw

        if job:
            job.progress = 100
            job.log("Graph build complete")
            job.status = "done"
            await broadcast(job)
        """
        Build a k-NN graph over all current embeddings and save it to disk.
        Uses FAISS HNSW index.
        """
        if self.index is None or self.count == 0:
            raise RuntimeError("No embeddings indexed yet, cannot build graph.")

        # load embeddings again (we don’t store them in index)
        entries = self._get_all()
        texts = [e["text"] for e in entries]

        model_id = self.meta["model"]
        model = get_model(model_id)()
        await asyncio.to_thread(model.load, CACHE_FOLDER)
        embs = await asyncio.to_thread(model.embed, texts)
        embs = l2norm(embs.astype(np.float32))

        N, d = embs.shape
        index = faiss.IndexHNSWFlat(d, 32)
        index.hnsw.efConstruction = 200
        index.add(embs)

        D, I = index.search(embs, k + 1)  # include self

        graph = {}
        for i in range(N):
            graph[i] = [(int(j), float(dist)) for dist, j in zip(D[i][1:], I[i][1:])]

        with open(self.graph_path, "wb") as f:
            pickle.dump(graph, f)

        self._graph = graph
        return graph


def get_store(name: str):
    store_path = STORES_DIR / name
    if not store_path.exists() or not store_path.is_dir():
        raise FileNotFoundError(f"Store not found: {name}")
    return Store(store_path)
