import argparse
import uuid
import time
import json
import logging
from datetime import datetime
from backend.models.trainer import fine_tune_model
from backend.core.engine import engine

logger = logging.getLogger("brainzCLI")
logging.basicConfig(level=logging.INFO)

def load_txt(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines() if line.strip()]

def load_jsonl(path: str) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        return [json.loads(line)["text"] for line in f if line.strip()]

def estimate_tokens(texts: list[str]) -> int:
    try:
        tokenizer = engine.get_model()["tokenizer"]
        return sum(len(tokenizer.encode(t)) for t in texts)
    except Exception:
        return -1  # If tokenizer isn't available

def main():
    parser = argparse.ArgumentParser(description="Train brainzOS with custom prompts")
    parser.add_argument("--file", type=str, required=True, help="Path to training data file")
    parser.add_argument("--format", type=str, choices=["txt", "jsonl"], default="txt", help="File format")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not train")
    parser.add_argument("--tags", type=str, nargs='*', help="Optional metadata tags")
    parser.add_argument("--source", type=str, default="cli", help="Training data origin")

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

    token_count = estimate_tokens(texts)
    logger.info(f"[{session_id}] Loaded {len(texts)} prompts (estimated tokens: {token_count})")

    # Preview
    if args.dry_run:
        print("[✓] Dry run complete. Training skipped.")
        print(f"[Info] Samples loaded: {len(texts)}")
        print(f"[Info] Token estimate: {token_count if token_count > 0 else 'unavailable'}")
        print(f"[Info] Tags: {args.tags}")
        print(f"[Info] Source: {args.source}")
        print(f"[Info] Session ID: {session_id}")
        return

    # Run fine-tuning
    try:
        print(f"[+] Starting fine-tuning with {len(texts)} samples...")
        fine_tune_model(texts)
        duration = round(time.time() - start_time, 2)
        print(f"[✓] Training complete in {duration}s.")
    except Exception as e:
        print(f"[✗] Training failed: {e}")
        logger.error(f"[{session_id}] Training error: {e}")

if __name__ == "__main__":
    main()
