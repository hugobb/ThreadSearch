from typing import Dict, List, Type, TypedDict
from .nomic_ai import NomicEmbedTextV15
from .base import BaseEmbeddingModel

class ModelSpec(TypedDict):
    repo: str
    name: str
    description: str
    tags: List[str]
    cls: Type[BaseEmbeddingModel]

MODELS: Dict[str, ModelSpec] = {
    "nomic-ai/nomic-embed-text-v1.5": {
        "repo": "nomic-ai/nomic-embed-text-v1.5",
        "name": "nomic-embed-text-v1.5",
        "description": "Small, fast, general-purpose embeddings",
        "tags": ["lightweight", "fast"],
        "cls": NomicEmbedTextV15,
    }
}

def get_model(repo_id: str) -> Type[BaseEmbeddingModel]:
    return MODELS[repo_id]["cls"]