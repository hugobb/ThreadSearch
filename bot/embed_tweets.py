"""
Precompute embeddings for all tweets and save FAISS index + corpus
Input: TSV file (one tweet per line)

Usage:
    python embed_tweets.py --input tweets.tsv --output_dir data --batch_size 64
"""
import argparse
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import tqdm


def main():
    parser = argparse.ArgumentParser(description="Embed tweets and save FAISS index")
    parser.add_argument(
        "--input", type=str, default="tweets.tsv",
        help="Path to TSV file with one tweet per line"
    )
    parser.add_argument(
        "--output_dir", type=str, default="data",
        help="Directory where index and tweets will be saved"
    )
    parser.add_argument(
        "--batch_size", type=int, default=64,
        help="Batch size for embedding computation"
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)

    index_file = output_dir / "tweets.index"
    tweets_out = output_dir / "tweets.txt"

    if not input_path.exists():
        raise FileNotFoundError(f"❌ Tweets file not found: {input_path}")

    # Load tweets lazily
    with open(input_path, "r", encoding="utf-8") as f:
        tweets = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(tweets)} tweets from {input_path}")

    # Save tweets immediately (so we don’t hold them in RAM twice)
    with open(tweets_out, "w", encoding="utf-8") as f:
        for t in tweets:
            f.write(t + "\n")

    # Load embedding model
    model_name = "all-MiniLM-L6-v2"
    embedder = SentenceTransformer(model_name)

    # Initialize FAISS index once we know embedding dimension
    print("Warmup to get embedding dimension...")
    test_emb = embedder.encode([tweets[0]], normalize_embeddings=True, convert_to_numpy=True)
    dim = test_emb.shape[1]
    index = faiss.IndexFlatIP(dim)

    # Compute + add to FAISS incrementally
    print("Computing embeddings & building FAISS index...")
    for i in tqdm.tqdm(range(0, len(tweets), args.batch_size), unit="batch"):
        batch = tweets[i:i + args.batch_size]
        embs = embedder.encode(batch, normalize_embeddings=True, convert_to_numpy=True)
        index.add(embs)  # directly add to index
        # Free memory for this batch
        del embs

    # Save FAISS index
    faiss.write_index(index, str(index_file))
    print(f"✅ Saved {len(tweets)} tweets and FAISS index to {output_dir}")


if __name__ == "__main__":
    main()
