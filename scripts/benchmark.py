import time
import uuid
import json
import statistics
from datetime import datetime
from backend.models.infer import generate_response
from backend.core.engine import engine
from typing import Optional

try:
    from rich import print as rprint
    use_color = True
except ImportError:
    use_color = False

def benchmark_model(
    prompt: str = "Define Solana in 1 sentence.",
    runs: int = 5,
    warmup: bool = True,
    max_tokens: int = 100,
    temperature: float = 0.7,
    save_path: Optional[str] = None
):
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    durations = []
    token_counts = []
    errors = 0

    print(f"\n[brainzOS] Starting benchmark session: {session_id}")

    # Optional warm-up run to stabilize performance
    if warmup:
        try:
            generate_response(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            print("[✓] Warm-up run complete.")
        except Exception:
            print("[!] Warm-up run failed.")

    for i in range(runs):
        try:
            start = time.time()
            response = generate_response(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            end = time.time()
            durations.append(end - start)

            # Estimate token length (if tokenizer available)
            tokenizer = engine.get_model()["tokenizer"]
            token_count = len(tokenizer.encode(response))
            token_counts.append(token_count)
        except Exception as e:
            print(f"[✗] Error during run {i+1}: {e}")
            errors += 1

    if not durations:
        print("[!] No successful runs. Benchmark aborted.")
        return

    # Stats
    avg_latency = sum(durations) / len(durations)
    min_latency = min(durations)
    max_latency = max(durations)
    median_latency = statistics.median(durations)
    total_tokens = sum(token_counts)
    throughput = total_tokens / sum(durations)

    # Output
    if use_color:
        rprint("\n[bold green]--- Benchmark Results ---[/bold green]")
        rprint(f"[bold]Prompt:[/bold] {prompt}")
        rprint(f"[bold]Runs:[/bold] {runs} (errors: {errors})")
        rprint(f"[bold]Average Latency:[/bold] {avg_latency:.2f}s")
        rprint(f"[bold]Median:[/bold] {median_latency:.2f}s")
        rprint(f"[bold]Min:[/bold] {min_latency:.2f}s")
        rprint(f"[bold]Max:[/bold] {max_latency:.2f}s")
        rprint(f"[bold]Total Tokens:[/bold] {total_tokens}")
        rprint(f"[bold]Throughput:[/bold] {throughput:.2f} tokens/sec")
    else:
        print("\n--- Benchmark Results ---")
        print(f"Prompt: {prompt}")
        print(f"Runs: {runs} (errors: {errors})")
        print(f"Average Latency: {avg_latency:.2f}s")
        print(f"Median: {median_latency:.2f}s")
        print(f"Min: {min_latency:.2f}s")
        print(f"Max: {max_latency:.2f}s")
        print(f"Total Tokens: {total_tokens}")
        print(f"Throughput: {throughput:.2f} tokens/sec")

    if save_path:
        output = {
            "session_id": session_id,
            "timestamp": timestamp,
            "prompt": prompt,
            "runs": runs,
            "errors": errors,
            "latencies": durations,
            "avg_latency": avg_latency,
            "median_latency": median_latency,
            "min_latency": min_latency,
            "max_latency": max_latency,
            "total_tokens": total_tokens,
            "throughput": throughput,
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"[✓] Benchmark results saved to: {save_path}")


if __name__ == "__main__":
    benchmark_model()
