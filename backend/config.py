from pathlib import Path

CACHE_FOLDER = Path("./.cache/huggingface")
STORES_DIR = Path("./.cache/stores")

STORES_DIR.mkdir(parents=True, exist_ok=True)