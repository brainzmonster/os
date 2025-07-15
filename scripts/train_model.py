import uuid
import time
import argparse
from datetime import datetime

from backend.models.trainer import fine_tune_model
from backend.services.memory_service import get_recent_prompts
from backend.core.engine import engine

def estimate_tokens(texts):
    try:
        tokenizer = engine.get_model()["tokenizer"]
        return sum(len(tokenizer.encode(txt)) for txt in texts)
    except Exception:
        return -1

def main():
    parser = argparse.ArgumentParser(description="Train brainzOS using recent memory prompts")
    parser.add_argument("--limit", type=int, default=20, help="Number of recent prompts to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry mode (preview only)")
    parser.add_argument("--min-length", type=int, default=10, help="Minimum word length filter for prompts")
    parser.add_argument("--log-file", type=str, help="Optional path to save training summary")
    args = parser.parse_args()

    session_id = str(uuid.uuid4())
    start_ts = datetime.utcnow().isoformat()
    start_time = time.time()

    print(f"\n[brainzOS] Training Session: {session_id}")
    print("[~] Collecting recent prompts from memory...")

    prompts = get_recent_prompts(limit=args.limit)
    raw_texts = [p.prompt for p in prompts]
    texts = [t for t in raw_texts if len(t.split()) >= args.min_length]

    if not texts:
        print("[!] No qualifying prompts found.")
        return

    print(f"[✓] {len(texts)} prompts selected (filtered by min {args.min_length} words)")

    token_count = estimate_tokens(texts)
    print(f"[~] Estimated token count: {token_count if token_count >= 0 else 'unknown'}")

    if args.dry_run:
        print("[✓] Dry-run enabled — skipping training.")
    else:
        print("[→] Starting model fine-tuning...")
        fine_tune_model(texts)
        print("[✓] Training complete.")

    duration = round(time.time() - start_time, 2)
    summary = {
        "session_id": session_id,
        "timestamp": start_ts,
        "duration_sec": duration,
        "total_prompts": len(prompts),
        "qualified_prompts": len(texts),
        "token_estimate": token_count,
        "dry_run": args.dry_run
    }

    print("\n--- Training Summary ---")
    for k, v in summary.items():
        print(f"{k}: {v}")

    if args.log_file:
        try:
            import json
            with open(args.log_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            print(f"[✓] Summary written to: {args.log_file}")
        except Exception as e:
            print(f"[!] Failed to write log: {e}")

if __name__ == "__main__":
    main()
