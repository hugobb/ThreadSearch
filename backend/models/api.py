from fastapi import APIRouter
from pydantic import BaseModel
from .registry import MODELS, get_model
from config import CACHE_FOLDER

router = APIRouter()

class DownloadModelReq(BaseModel):
    repo_id: str

class Query(BaseModel):
    model: str
    text: str


@router.get("/models/catalog")
def catalog():
    return {
        "models": [
            {
                "id": model_id,
                **{k: v for k, v in entry.items() if k != "cls"}
            }
            for model_id, entry in MODELS.items()
        ]
    }

@router.post("/models/download")
def download_model(req: DownloadModelReq):
    model_class = get_model(req.repo_id)
    model_class.download(cache_dir=CACHE_FOLDER)
    return {"ok": True, "repo_id": req.repo_id}

@router.get("/models/local")
def list_local_models():
    local = []
    if CACHE_FOLDER.exists():
        for d in CACHE_FOLDER.glob("models--*"):
            repo = d.name.replace("models--", "").replace("--", "/")
            local.append(repo)
    return {"local_models": local}
