"""
Generate a conversation using precomputed tweet embeddings.

Usage:
    python generate_conversation.py \
        --input_dir data \
        --out_dir conversations \
        --prefix convo \
        --length 10 \
        --mode polarized \
        --seed "The government is lying to us"
"""

import argparse
import faiss
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import json
import re

# Load API keys from .env
load_dotenv()
client = OpenAI()


def load_tweets_and_index(input_dir: Path):
    tweets_file = input_dir / "tweets.txt"
    index_file = input_dir / "tweets.index"

    if not tweets_file.exists() or not index_file.exists():
        raise FileNotFoundError("❌ tweets.txt or tweets.index not found in input_dir")

    with open(tweets_file, "r", encoding="utf-8") as f:
        tweets = [line.strip() for line in f if line.strip()]

    index = faiss.read_index(str(index_file))
    return tweets, index


def embed_query(text: str, model="all-MiniLM-L6-v2"):
    from sentence_transformers import SentenceTransformer
    embedder = SentenceTransformer(model)
    vec = embedder.encode([text], normalize_embeddings=True, convert_to_numpy=True)
    return vec


def retrieve_candidates(query, tweets, index, used, top_k=20):
    q_emb = embed_query(query)
    sims, ids = index.search(q_emb, top_k)
    sims, ids = sims[0], ids[0]
    results = []
    for idx, score in zip(ids, sims):
        if idx < 0:
            continue
        if int(idx) in used:
            continue
        results.append((tweets[int(idx)], float(score), int(idx)))
        if len(results) >= 5:  # only return top 5 unseen
            break
    return results


def generate_turn(history: list[str], mode: str, next_speaker: str) -> str:
    recent = history[-8:]

    style_line = (
        "oppose the previous speaker strongly in a civil tone"
        if mode == "polarized"
        else "support and reinforce the previous speaker"
    )

    system = (
        "You produce exactly ONE short utterance for the requested speaker.\n"
        "Rules:\n"
        "- Output MUST be JSON with one field: {\"utterance\": \"...\"}\n"
        "- No speaker labels, no quotes, no markdown, no lists.\n"
        "- Keep it concise (5–25 words).\n"
        "- Do not simulate multiple turns.\n"
    )

    user = (
        f"CONTEXT (most recent last):\n"
        + "\n".join(recent)
        + "\n\n"
        f"TASK: Write exactly one short sentence for {next_speaker} that should {style_line}.\n"
        'Return ONLY a minified JSON object of the form: {"utterance":"..."}'
    )

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.5,
        max_tokens=64,
        stop=["\n\n", "Speaker A:", "Speaker B:"],
    )
    content = resp.choices[0].message.content.strip()

    try:
        data = json.loads(content)
        text = data.get("utterance", "").strip()
    except Exception:
        line = content.splitlines()[0]
        line = re.sub(r"^Speaker\s*[AB]\s*:\s*", "", line).strip()
        m = re.search(r"([^.?!]+[.?!])", line)
        text = (m.group(1) if m else line).strip()

    text = re.sub(r"^Speaker\s*[AB]\s*:\s*", "", text).strip()
    return text


def main():
    parser = argparse.ArgumentParser(description="Generate debate/echo conversation from tweet corpus")
    parser.add_argument("--input_dir", type=str, default="data", help="Directory with tweets.txt and tweets.index")
    parser.add_argument("--out_dir", type=str, default="conversations", help="Folder to save generated conversations")
    parser.add_argument("--prefix", type=str, default="convo", help="Filename prefix")
    parser.add_argument("--length", type=int, default=10, help="Number of turns in conversation")
    parser.add_argument("--mode", type=str, choices=["polarized", "echo"], default="polarized", help="Conversation mode")
    parser.add_argument("--seed", type=str, required=True, help="Seed statement for the conversation")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"{args.prefix}_{args.mode}_{timestamp}.txt"

    tweets, index = load_tweets_and_index(input_dir)

    conversation = []
    used_ids = set()
    seed = args.seed.strip()
    conversation.append(f"Speaker A: {seed}")
    print(f"👤 Speaker A (seed): {seed}\n")

    for i in range(args.length - 1):
        next_speaker = "Speaker B" if i % 2 == 0 else "Speaker A"
        candidate = generate_turn(conversation, args.mode, next_speaker)
        print(f"🤖 Candidate for {next_speaker}: {candidate}")

        candidates = retrieve_candidates(candidate, tweets, index, used_ids, top_k=50)
        if not candidates:
            print("⚠️ No unseen tweets left, stopping early.")
            break

        best_tweet, best_score, best_id = candidates[0]
        used_ids.add(best_id)
        line = f"{next_speaker}: {best_tweet}"
        conversation.append(line)
        print(f"✅ Chosen for {next_speaker}: ({best_score:.4f}) {best_tweet}\n")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write("\n".join(conversation))

    print(f"\n✅ Conversation saved to {out_file}")


if __name__ == "__main__":
    main()
