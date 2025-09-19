import argparse
import uuid
import time
import logging
from typing import Dict

from backend.models.infer import generate_response
from backend.core.engine import engine

logger = logging.getLogger("brainzCLI")
logging.basicConfig(level=logging.INFO)


# -------------------------------------------------------------------
# NEW: Token accounting helper
# -------------------------------------------------------------------
def estimate_token_counts(prompt_text: str, output_text: str) -> Dict[str, int]:
    """
    Best-effort token accounting using the active engine tokenizer.

    Returns a dict with:
      {
        "prompt_tokens": <int or -1>,
        "output_tokens": <int or -1>,
        "total_tokens":  <int or -1>
      }

    If the tokenizer cannot be accessed, all values fall back to -1.
    This function is intentionally side-effect free and safe to call
    even when the engine hasn't fully booted.
    """
    try:
        llm = engine.get_model() or {}
        tokenizer = llm.get("tokenizer", None)
        if tokenizer is None:
            return {"prompt_tokens": -1, "output_tokens": -1, "total_tokens": -1}

        prompt_tokens = len(tokenizer.encode(prompt_text)) if prompt_text else 0
        output_tokens = len(tokenizer.encode(output_text)) if output_text else 0
        return {
            "prompt_tokens": prompt_tokens,
            "output_tokens": output_tokens,
            "total_tokens": prompt_tokens + output_tokens,
        }
    except Exception:
        # Keep CLI resilient: never crash on token-estimation
        return {"prompt_tokens": -1, "output_tokens": -1, "total_tokens": -1}


def main():
    """
    CLI entrypoint to query the brainzOS LLM.

    - Supports optional system prompt prepending.
    - Dry-run mode to inspect parameters without invoking generation.
    - Optional output file write.
    - (NEW) --show_tokens to print prompt/output/total token counts.
    """
    parser = argparse.ArgumentParser(description="Query brainzOS LLM via CLI")
    parser.add_argument("--prompt", type=str, required=True, help="Input prompt for the model")
    parser.add_argument("--max_tokens", type=int, default=100, help="Maximum tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature (0.0 - 1.0)")
    parser.add_argument("--system_prompt", type=str, help="Optional system prompt to prepend")
    parser.add_argument("--dry_run", action="store_true", help="Simulate generation without executing")
    parser.add_argument("--output_file", type=str, help="Optional path to write output to file")
    # NEW: optionally report token counts using the loaded tokenizer
    parser.add_argument("--show_tokens", action="store_true", help="Print prompt/output/total token counts")

    args = parser.parse_args()

    session_id = str(uuid.uuid4())
    start_time = time.time()

    # Compose final prompt (system + user) without changing original semantics
    full_prompt = f"{args.system_prompt}\n{args.prompt}" if args.system_prompt else args.prompt

    # Dry-run: just echo parameters and exit
    if args.dry_run:
        print("[✓] Dry run — no generation performed.")
        print(f"[Info] Prompt: {args.prompt}")
        print(f"[Info] System Prompt: {args.system_prompt or 'None'}")
        print(f"[Info] Max Tokens: {args.max_tokens}")
        print(f"[Info] Temperature: {args.temperature}")
        print(f"[Info] Session ID: {session_id}")

        if args.show_tokens:
            counts = estimate_token_counts(full_prompt, "")
            print(f"[Tokens] prompt={counts['prompt_tokens']}, output={counts['output_tokens']}, total={counts['total_tokens']}")
        return

    try:
        print("[brainzOS] Generating response...")
        output = generate_response(
            prompt=full_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        duration = round(time.time() - start_time, 2)

        # Try to read model name defensively
        model_info = engine.get_model() or {}
        model_obj = model_info.get("model")
        model_name = getattr(model_obj, "name_or_path", "unknown") if model_obj is not None else "unknown"

        # Pretty print model output
        print("\n[Model Output]")
        print("=" * 60)
        print(output)
        print("=" * 60)

        print(f"\n[Info] Model: {model_name}")
        print(f"[Info] Inference time: {duration}s")
        print(f"[Info] Session ID: {session_id}")

        # NEW: Optional token accounting printout
        if args.show_tokens:
            counts = estimate_token_counts(full_prompt, output)
            print(f"[Tokens] prompt={counts['prompt_tokens']}, output={counts['output_tokens']}, total={counts['total_tokens']}")

        # Optional: persist output
        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"[✓] Output saved to: {args.output_file}")

    except Exception as e:
        logger.error(f"[{session_id}] Error during inference: {str(e)}")
        print(f"[✗] Generation failed: {str(e)}")


if __name__ == "__main__":
    main()
