from typing import List, Optional, Protocol

import numpy as np


class BaseModel(Protocol):
    def encode(self, texts: List[str]) -> np.ndarray:
        ...

class BaseEmbeddingModel:
    model: Optional[BaseModel] = None

    @classmethod
    def download(cls, cache_dir: Optional[str] = None):
        """Download model weights to local cache (no memory load)."""
        raise NotImplementedError

    def load(self, cache_dir: Optional[str] = None):
        """Load model into memory (tokenizer, encoder, etc.)."""
        raise NotImplementedError

    def embed(self, texts: List[str]) -> np.ndarray:
        """Encode texts into embeddings."""
        raise NotImplementedError
    
    def unload(self):
        """Unload model from memory."""
        self.model = None