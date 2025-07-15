import argparse
import uuid
import time
import logging
from backend.models.infer import generate_response
from backend.core.engine import engine

logger = logging.getLogger("brainzCLI")
logging.basicConfig(level=logging.INFO)

def main():
    parser = argparse.ArgumentParser(description="Query brainzOS LLM via CLI")
    parser.add_argument("--prompt", type=str, required=True, help="Input prompt for the model")
    parser.add_argument("--max_tokens", type=int, default=100, help="Maximum tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.7, help="Sampling temperature (0.0 - 1.0)")
    parser.add_argument("--system_prompt", type=str, help="Optional system prompt to prepend")
    parser.add_argument("--dry_run", action="store_true", help="Simulate generation without executing")
    parser.add_argument("--output_file", type=str, help="Optional path to write output to file")
    args = parser.parse_args()

    session_id = str(uuid.uuid4())
    start_time = time.time()

    full_prompt = f"{args.system_prompt}\n{args.prompt}" if args.system_prompt else args.prompt

    if args.dry_run:
        print("[✓] Dry run — no generation performed.")
        print(f"[Info] Prompt: {args.prompt}")
        print(f"[Info] System Prompt: {args.system_prompt or 'None'}")
        print(f"[Info] Max Tokens: {args.max_tokens}")
        print(f"[Info] Temperature: {args.temperature}")
        print(f"[Info] Session ID: {session_id}")
        return

    try:
        print("[brainzOS] Generating response...")
        output = generate_response(
            prompt=full_prompt,
            max_tokens=args.max_tokens,
            temperature=args.temperature,
        )
        duration = round(time.time() - start_time, 2)

        model_name = engine.get_model().get("model").name_or_path if "model" in engine.get_model() else "unknown"

        print("\n[Model Output]")
        print("=" * 60)
        print(output)
        print("=" * 60)

        print(f"\n[Info] Model: {model_name}")
        print(f"[Info] Inference time: {duration}s")
        print(f"[Info] Session ID: {session_id}")

        if args.output_file:
            with open(args.output_file, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"[✓] Output saved to: {args.output_file}")

    except Exception as e:
        logger.error(f"[{session_id}] Error during inference: {str(e)}")
        print(f"[✗] Generation failed: {str(e)}")

if __name__ == "__main__":
    main()
