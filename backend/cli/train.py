import argparse
import uuid
import time
import json
import logging
from datetime import datetime
from typing import List, Tuple

from backend.models.trainer import fine_tune_model
from backend.core.engine import engine

logger = logging.getLogger("brainzCLI")
logging.basicConfig(level=logging.INFO)


# ----------------------------
# IO HELPERS
# ----------------------------
def load_txt(path: str) -> list[str]:
    """
    Load a plain-text file where each non-empty line is a training sample.
    """
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]


def load_jsonl(path: str) -> list[str]:
    """
    Load a JSONL file with a 'text' field per line.
    Backward-compatible: if a line has {"prompt": "...", "completion": "..."},
    it will concatenate them into a single 'text' sample.
    """
    texts: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            obj = json.loads(raw)
            if "text" in obj and obj["text"]:
                texts.append(str(obj["text"]).strip())
            elif "prompt" in obj and "completion" in obj:
                # Simple SFT-style flattening for single-text training
                p = str(obj["prompt"]).strip()
                c = str(obj["completion"]).strip()
                texts.append(f"<|user|>: {p}\n<|assistant|>: {c}")
    return texts


def estimate_tokens(texts: list[str]) -> int:
    """
    Best-effort token estimate using the active engine tokenizer.
    Returns -1 if tokenizer is unavailable.
    """
    try:
        tokenizer = engine.get_model()["tokenizer"]
        return sum(len(tokenizer.encode(t)) for t in texts)
    except Exception:
        return -1  # If tokenizer isn't available


# ----------------------------
# NEW: DATA PREP + BATCH TRAINING
# ----------------------------
def sanitize_texts(
    texts: List[str],
    min_words: int = 1,
    dedupe: bool = False
) -> Tuple[List[str], dict]:
    """
    Clean and filter raw texts prior to training in a conservative, non-destructive way.

    - Drops entries shorter than `min_words` (whitespace-split).
    - Optionally deduplicates while preserving order.
    - Returns (filtered_texts, stats).

    This function does NOT change formatting or casing, to keep the behavior
    of fine_tune_model() identical; it only filters obvious low-signal samples.
    """
    original = len(texts)

    # Filter by min length (in words)
    filtered = [t for t in texts if len(t.split()) >= max(0, min_words)]

    # Optional dedupe with stable order
    if dedupe:
        seen = set()
        stable = []
        for t in filtered:
            if t not in seen:
                seen.add(t)
                stable.append(t)
        filtered = stable

    stats = {
        "original": original,
        "after_min_words": len(filtered),
        "deduped": dedupe,
        "removed": original - len(filtered),
        "min_words": min_words
    }
    return filtered, stats


def train_in_batches(
    texts: List[str],
    batch_size: int = 0,
    inter_batch_sleep: float = 0.0
) -> int:
    """
    Train in micro-batches by repeatedly calling fine_tune_model(text_chunk).

    Why?
    - Keeps memory footprint predictable for very large corpora.
    - Allows checkpoints/metrics between chunks outside of fine_tune_model().
    - Preserves the existing fine_tune_model() contract (List[str] in).

    Returns:
        Total number of samples trained.
    """
    if batch_size is None or batch_size <= 0:
        # Single-shot: preserve original behavior exactly
        fine_tune_model(texts)
        return len(texts)

    trained = 0
    total = len(texts)
    for i in range(0, total, batch_size):
        chunk = texts[i:i + batch_size]
        logger.info(f"[batch-train] chunk {i // batch_size + 1} / {((total - 1) // batch_size) + 1} "
                    f"({len(chunk)} samples)")
        fine_tune_model(chunk)
        trained += len(chunk)
        if inter_batch_sleep > 0:
            time.sleep(inter_batch_sleep)
    return trained


# ----------------------------
# MAIN CLI
# ----------------------------
def main():
    parser = argparse.ArgumentParser(description="Train brainzOS with custom prompts")
    parser.add_argument("--file", type=str, required=True, help="Path to training data file")
    parser.add_argument("--format", type=str, choices=["txt", "jsonl"], default="txt", help="File format")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not train")
    parser.add_argument("--tags", type=str, nargs='*', help="Optional metadata tags")
    parser.add_argument("--source", type=str, default="cli", help="Training data origin")

    # NEW options (backward-compatible defaults)
    parser.add_argument("--min-words", type=int, default=1, help="Filter out samples shorter than N words")
    parser.add_argument("--dedupe", action="store_true", help="Remove duplicate samples before training")
    parser.add_argument("--batch-size", type=int, default=0, help="Micro-batch size; 0 means single-shot")
    parser.add_argument("--sleep", type=float, default=0.0, help="Seconds to sleep between batches")
    parser.add_argument("--preview", type=int, default=3, help="Show the first N samples as a preview")

    args = parser.parse_args()
    session_id = str(uuid.uuid4())
    start_time = time.time()

    # Load file
    try:
        if args.format == "jsonl":
            texts = load_jsonl(args.file)
        else:
            texts = load_txt(args.file)
    except Exception as e:
        print(f"[!] Failed to load file: {e}")
        return

    if not texts:
        print("[!] No valid training texts found.")
        return

    # NEW: sanitize & summarize dataset
    prepared, prep_stats = sanitize_texts(texts, min_words=args.min_words, dedupe=args.dedupe)
    if not prepared:
        print("[!] No samples left after filtering. Adjust --min-words or remove --dedupe.")
        return

    # Preview a few samples, non-destructive
    if args.preview > 0:
        print("\n--- Preview Samples ---")
        for i, s in enumerate(prepared[:args.preview], start=1):
            print(f"[{i}] {s[:200]}{'...' if len(s) > 200 else ''}")
        print("-----------------------\n")

    token_count = estimate_tokens(prepared)
    logger.info(
        f"[{session_id}] Loaded {len(texts)} → {len(prepared)} samples "
        f"(removed {prep_stats['removed']}, min_words={prep_stats['min_words']}, deduped={prep_stats['deduped']}); "
        f"estimated tokens: {token_count}"
    )

    # Dry run: only report stats and exit
    if args.dry_run:
        print("[✓] Dry run complete. Training skipped.")
        print(f"[Info] Samples loaded: {len(texts)}")
        print(f"[Info] Qualified after filtering: {len(prepared)}")
        print(f"[Info] Removed by filter: {prep_stats['removed']}")
        print(f"[Info] Token estimate: {token_count if token_count > 0 else 'unavailable'}")
        print(f"[Info] Tags: {args.tags}")
        print(f"[Info] Source: {args.source}")
        print(f"[Info] Session ID: {session_id}")
        return

    # Train (single-shot or micro-batches)
    try:
        if args.batch_size and args.batch_size > 0:
            print(f"[+] Starting batched fine-tuning: batch_size={args.batch_size}, sleep={args.sleep}s")
            trained = train_in_batches(prepared, batch_size=args.batch_size, inter_batch_sleep=args.sleep)
        else:
            print(f"[+] Starting fine-tuning with {len(prepared)} samples (single-shot)...")
            fine_tune_model(prepared)
            trained = len(prepared)

        duration = round(time.time() - start_time, 2)
        print(f"[✓] Training complete in {duration}s. Trained on {trained} samples.")
    except Exception as e:
        print(f"[✗] Training failed: {e}")
        logger.error(f"[{session_id}] Training error: {e}")


if __name__ == "__main__":
    main()
