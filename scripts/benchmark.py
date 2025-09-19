import time
import uuid
import json
import statistics
from datetime import datetime
from typing import Optional, Iterable, Dict, Any

from backend.models.infer import generate_response
from backend.core.engine import engine

# Pretty terminal output if 'rich' is installed; falls back to plain prints.
try:
    from rich import print as rprint
    use_color = True
except ImportError:
    use_color = False


def _get_tokenizer_safe():
    """
    Internal helper to fetch the active tokenizer from the engine.
    Returns the tokenizer instance or None if unavailable.
    """
    try:
        return engine.get_model()["tokenizer"]
    except Exception:
        return None


def estimate_tokens(texts: Iterable[str]) -> int:
    """
    Estimate total token count for a collection of texts using the active tokenizer.
    Returns -1 if a tokenizer is not available or an error occurs.
    """
    tok = _get_tokenizer_safe()
    if tok is None:
        return -1
    try:
        return sum(len(tok.encode(txt)) for txt in texts)
    except Exception:
        return -1


def percentile_stats(values: Iterable[float], ps: Iterable[float] = (0.5, 0.9, 0.95, 0.99)) -> Dict[str, float]:
    """
    NEW: Compute percentile statistics for a list of numbers (e.g., latencies).
    Percentiles are expressed as fractions in (0,1], e.g., 0.9 for p90.

    Returns a dict like: {"p50": ..., "p90": ..., "p95": ..., "p99": ...}
    """
    vals = sorted(values)
    n = len(vals)
    if n == 0:
        return {f"p{int(p*100)}": float("nan") for p in ps}

    def _pct(p: float) -> float:
        # Use nearest-rank method (common in ops dashboards)
        idx = min(max(int(round(p * n + 0.5)) - 1, 0), n - 1)
        return vals[idx]

    return {f"p{int(p*100)}": _pct(p) for p in ps}


def benchmark_model(
    prompt: str = "Define Solana in 1 sentence.",
    runs: int = 5,
    warmup: bool = True,
    max_tokens: int = 100,
    temperature: float = 0.7,
    save_path: Optional[str] = None
):
    """
    Run a latency/throughput benchmark against the active model for a single prompt.
    Produces aggregate latency stats, token throughput, and optional JSON export.
    """
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    durations = []
    token_counts = []
    errors = 0

    print(f"\n[brainzOS] Starting benchmark session: {session_id}")

    # Optional warm-up run to stabilize any lazy init or JIT paths.
    if warmup:
        try:
            generate_response(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            print("[✓] Warm-up run complete.")
        except Exception:
            print("[!] Warm-up run failed.")

    # Main benchmark loop
    for i in range(runs):
        try:
            start = time.time()
            response = generate_response(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            end = time.time()
            durations.append(end - start)

            # Estimate tokens for the produced response
            tok = _get_tokenizer_safe()
            token_count = len(tok.encode(response)) if tok is not None else 0
            token_counts.append(token_count)

        except Exception as e:
            print(f"[✗] Error during run {i+1}: {e}")
            errors += 1

    if not durations:
        print("[!] No successful runs. Benchmark aborted.")
        return

    # Aggregate stats
    avg_latency = sum(durations) / len(durations)
    min_latency = min(durations)
    max_latency = max(durations)
    median_latency = statistics.median(durations)
    pct = percentile_stats(durations)  # NEW: percentile breakdown (p50/p90/p95/p99)

    total_tokens = sum(token_counts)
    total_time = sum(durations)
    throughput = (total_tokens / total_time) if total_time > 0 else 0.0

    # Output block
    if use_color:
        rprint("\n[bold green]--- Benchmark Results ---[/bold green]")
        rprint(f"[bold]Prompt:[/bold] {prompt}")
        rprint(f"[bold]Runs:[/bold] {runs} (errors: {errors})")
        rprint(f"[bold]Average Latency:[/bold] {avg_latency:.2f}s")
        rprint(f"[bold]Median:[/bold] {median_latency:.2f}s")
        rprint(f"[bold]Min:[/bold] {min_latency:.2f}s    [bold]Max:[/bold] {max_latency:.2f}s")
        rprint(f"[bold]p50:[/bold] {pct.get('p50', float('nan')):.2f}s  "
               f"[bold]p90:[/bold] {pct.get('p90', float('nan')):.2f}s  "
               f"[bold]p95:[/bold] {pct.get('p95', float('nan')):.2f}s  "
               f"[bold]p99:[/bold] {pct.get('p99', float('nan')):.2f}s")
        rprint(f"[bold]Total Tokens:[/bold] {total_tokens}")
        rprint(f"[bold]Throughput:[/bold] {throughput:.2f} tokens/sec")
    else:
        print("\n--- Benchmark Results ---")
        print(f"Prompt: {prompt}")
        print(f"Runs: {runs} (errors: {errors})")
        print(f"Average Latency: {avg_latency:.2f}s")
        print(f"Median: {median_latency:.2f}s")
        print(f"Min: {min_latency:.2f}s  Max: {max_latency:.2f}s")
        print(f"p50: {pct.get('p50', float('nan')):.2f}s  "
              f"p90: {pct.get('p90', float('nan')):.2f}s  "
              f"p95: {pct.get('p95', float('nan')):.2f}s  "
              f"p99: {pct.get('p99', float('nan')):.2f}s")
        print(f"Total Tokens: {total_tokens}")
        print(f"Throughput: {throughput:.2f} tokens/sec")

    # Optional JSON export for dashboards/CI artifacts
    if save_path:
        output: Dict[str, Any] = {
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
            "percentiles": pct,  # NEW: include percentile breakdown in export
            "total_tokens": total_tokens,
            "throughput": throughput,
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
        print(f"[✓] Benchmark results saved to: {save_path}")


def benchmark_prompts(
    prompts: Iterable[str],
    runs: int = 3,
    max_tokens: int = 100,
    temperature: float = 0.7,
    warmup_each: bool = False,
    save_path: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """
    NEW: Batch benchmark multiple prompts in one go.
    Useful for comparing latency/throughput across prompt shapes (short vs. long, code vs. prose, etc.)

    Returns a mapping:
      {
        "<prompt>": {
           "avg_latency": ...,
           "median_latency": ...,
           "min_latency": ...,
           "max_latency": ...,
           "percentiles": {...},
           "total_tokens": ...,
           "throughput": ...,
           "errors": ...
        },
        ...
      }

    Notes:
    - Does not interfere with benchmark_model(); it's an additive utility.
    - Optionally writes a combined JSON file for dashboards.
    """
    results: Dict[str, Dict[str, Any]] = {}
    for prompt in prompts:
        durations = []
        token_counts = []
        errors = 0

        if warmup_each:
            try:
                generate_response(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
            except Exception:
                # Warm-up failure shouldn't kill the batch
                pass

        for _ in range(runs):
            try:
                t0 = time.time()
                resp = generate_response(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
                t1 = time.time()
                durations.append(t1 - t0)

                tok = _get_tokenizer_safe()
                token_counts.append(len(tok.encode(resp)) if tok is not None else 0)

            except Exception:
                errors += 1

        if durations:
            avg_latency = sum(durations) / len(durations)
            med_latency = statistics.median(durations)
            min_latency = min(durations)
            max_latency = max(durations)
            pct = percentile_stats(durations)

            total_tokens = sum(token_counts)
            total_time = sum(durations)
            throughput = (total_tokens / total_time) if total_time > 0 else 0.0
        else:
            avg_latency = med_latency = min_latency = max_latency = float("nan")
            pct = {k: float("nan") for k in ("p50", "p90", "p95", "p99")}
            total_tokens = 0
            throughput = 0.0

        results[prompt] = {
            "avg_latency": avg_latency,
            "median_latency": med_latency,
            "min_latency": min_latency,
            "max_latency": max_latency,
            "percentiles": pct,
            "total_tokens": total_tokens,
            "throughput": throughput,
            "errors": errors
        }

    if save_path:
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"[✓] Multi-prompt benchmark saved to: {save_path}")

    return results


if __name__ == "__main__":
    # Default single-prompt benchmark entry point
    benchmark_model()
