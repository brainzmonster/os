import uuid
import time
import argparse
from datetime import datetime

from backend.models.trainer import fine_tune_model
from backend.services.memory_service import get_recent_prompts
from backend.core.engine import engine

def estimate_tokens(texts):
    """
    Estimate token count of a list of texts using the current model's tokenizer.
    Returns -1 if tokenizer is not available or fails.
    """
    try:
        tokenizer = engine.get_model()["tokenizer"]
        return sum(len(tokenizer.encode(txt)) for txt in texts)
    except Exception:
        return -1

def build_training_data(prompts, min_length: int = 10, include_completions: bool = False) -> list:
    """
    Filters recent memory prompts and optionally includes completions.
    Only includes prompts with minimum word count.
    """
    filtered = []
    for p in prompts:
        if len(p.prompt.split()) >= min_length:
            if include_completions and hasattr(p, "completion") and p.completion:
                filtered.append({"prompt": p.prompt, "completion": p.completion})
            else:
                filtered.append(p.prompt)
    return filtered

def main():
    parser = argparse.ArgumentParser(description="Train brainzOS using recent memory prompts")
    parser.add_argument("--limit", type=int, default=20, help="Number of recent prompts to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry mode (preview only)")
    parser.add_argument("--min-length", type=int, default=10, help="Minimum word length filter for prompts")
    parser.add_argument("--log-file", type=str, help="Optional path to save training summary")
    parser.add_argument("--include-completions", action="store_true", help="Include prompt completions if available")
    args = parser.parse_args()

    session_id = str(uuid.uuid4())
    start_ts = datetime.utcnow().isoformat()
    start_time = time.time()

    print(f"\n[brainzOS] Training Session: {session_id}")
    print("[~] Collecting recent prompts from memory...")

    prompts = get_recent_prompts(limit=args.limit)
    training_data = build_training_data(
        prompts=prompts,
        min_length=args.min_length,
        include_completions=args.include_completions
    )

    if not training_data:
        print("[!] No qualifying prompts found.")
        return

    print(f"[✓] {len(training_data)} entries selected (filtered by min {args.min_length} words)")

    # Estimate token count
    if isinstance(training_data[0], dict):
        token_texts = [f"{d['prompt']} {d.get('completion', '')}" for d in training_data]
    else:
        token_texts = training_data

    token_count = estimate_tokens(token_texts)
    print(f"[~] Estimated token count: {token_count if token_count >= 0 else 'unknown'}")

    # Training logic
    if args.dry_run:
        print("[✓] Dry-run enabled — skipping training.")
    else:
        print("[→] Starting model fine-tuning...")
        fine_tune_model(training_data)
        print("[✓] Training complete.")

    # Summary
    duration = round(time.time() - start_time, 2)
    summary = {
        "session_id": session_id,
        "timestamp": start_ts,
        "duration_sec": duration,
        "total_prompts": len(prompts),
        "qualified": len(training_data),
        "token_estimate": token_count,
        "dry_run": args.dry_run,
        "include_completions": args.include_completions
    }

    print("\n--- Training Summary ---")
    for k, v in summary.items():
        print(f"{k}: {v}")

    # Optional log file
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
