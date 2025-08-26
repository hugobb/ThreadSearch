from pathlib import Path

CACHE_FOLDER = Path("./.cache/huggingface")
STORES_DIR = Path("./.cache/stores")

STORES_DIR.mkdir(exist_ok=True)