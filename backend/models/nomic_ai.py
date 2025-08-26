from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from .base import BaseEmbeddingModel

class NomicEmbedTextV15(BaseEmbeddingModel):
    repo_id: str = "nomic-ai/nomic-embed-text-v1.5"

    @classmethod
    def download(cls, cache_dir: Optional[str] = None):
        # Download model weights to local cache
        SentenceTransformer(cls.repo_id, trust_remote_code=True, cache_folder=cache_dir)

    def load(self, cache_dir: Optional[str] = None):
        self.model = SentenceTransformer(self.repo_id, trust_remote_code=True, local_files_only=True, cache_folder=cache_dir)

    def embed(self, texts: List[str]) -> np.ndarray:
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings