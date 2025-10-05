import time
from statistics import mean, median
from typing import List, Dict, Any

from backend.models.loader import load_model
from backend.models.infer import generate_response
from backend.utils.tokenizer import count_tokens  # Optional


def test_load_model(verbose: bool = True) -> dict:
    """
    Load the model and tokenizer, verify core structure and runtime properties.
    """
    result = {"test": "load_model", "status": "pass", "errors": []}

    try:
        start = time.time()
        llm = load_model()
        end = time.time()

        assert "model" in llm, "Missing model key"
        assert "tokenizer" in llm, "Missing tokenizer key"

        model = llm["model"]
        tokenizer = llm["tokenizer"]

        assert callable(getattr(model, "generate", None)), "Model lacks .generate()"
        assert hasattr(tokenizer, "encode"), "Tokenizer missing encode method"

        if verbose:
            print(f"[TEST] Model type: {type(model).__name__}")
            print(f"[TEST] Tokenizer type: {type(tokenizer).__name__}")
            print(f"[TEST] Load time: {round(end - start, 2)}s")

        result["load_time_sec"] = round(end - start, 2)

    except Exception as e:
        result["status"] = "fail"
        result["errors"].append(str(e))

    return result


def test_generate_response(verbose: bool = True, max_tokens: int = 100) -> dict:
    """
    Run a basic inference and validate result structure and quality.
    """
    result = {"test": "generate_response", "status": "pass", "errors": []}
    prompt = "What is Web3?"

    try:
        if verbose:
            print(f"[TEST] Prompt: {prompt}")
        start = time.time()
        output = generate_response(prompt, max_tokens=max_tokens)
        end = time.time()

        assert isinstance(output, str), "Output is not a string"
        assert len(output.strip()) > 0, "Output is empty"

        token_count = count_tokens(output) if "count_tokens" in globals() else len(output.split())

        if verbose:
            preview = output[:200] + ("..." if len(output) > 200 else "")
            print(f"[TEST] Output: {preview}")
            print(f"[TEST] Inference time: {round(end - start, 3)}s")
            print(f"[TEST] Tokens: ~{token_count}")

        result.update({
            "prompt": prompt,
            "output": output,
            "tokens": token_count,
            "duration": round(end - start, 3)
        })

    except Exception as e:
        result["status"] = "fail"
        result["errors"].append(str(e))

    return result


# ---------------------------------------------------------------------------
# NEW: Batch inference test with throughput & latency statistics
# ---------------------------------------------------------------------------
def test_batch_inference(
    prompts: List[str] | None = None,
    max_tokens: int = 64,
    temperature: float = 0.7,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Execute multiple prompts back-to-back to measure:
      - Per-sample latency
      - Per-sample token counts
      - Aggregate throughput (tokens/sec)
      - Min/Max/Avg/Median latency

    This test is useful in CI to catch performance regressions and
    to compare different model configs (quantization, LoRA, GPU vs CPU, etc.).

    Args:
        prompts: List of prompts to evaluate. If None, a default small suite is used.
        max_tokens: Generation cap per prompt.
        temperature: Sampling temperature for all prompts.
        verbose: Print a compact report to stdout.

    Returns:
        Dict with summary stats and per-sample records.
    """
    if prompts is None:
        prompts = [
            "Give a one-sentence definition of Solana.",
            "Name three use-cases for zero-knowledge proofs.",
            "Explain what a smart contract is, in simple terms.",
            "Compare rollups and validiums briefly.",
            "What is a Merkle tree used for?"
        ]

    latencies: List[float] = []
    token_counts: List[int] = []
    records: List[Dict[str, Any]] = []

    # Run each prompt and collect timing + token stats
    for idx, p in enumerate(prompts, start=1):
        try:
            t0 = time.time()
            out = generate_response(prompt=p, max_tokens=max_tokens, temperature=temperature)
            t1 = time.time()

            assert isinstance(out, str) and out.strip(), "Empty or invalid output."

            # Prefer brainz tokenizer if present; fallback to word-count
            tokens_out = count_tokens(out) if "count_tokens" in globals() else len(out.split())
            dt = round(t1 - t0, 4)

            latencies.append(dt)
            token_counts.append(tokens_out)

            records.append({
                "idx": idx,
                "prompt": p,
                "latency_sec": dt,
                "tokens_out": tokens_out,
                "preview": out[:160] + ("..." if len(out) > 160 else "")
            })

        except Exception as e:
            # If a single prompt fails, record the error but continue the batch.
            records.append({
                "idx": idx,
                "prompt": p,
                "error": str(e)
            })

    # If nothing succeeded, return a fail status
    successful = [r for r in records if "error" not in r]
    if not successful:
        return {
            "test": "batch_inference",
            "status": "fail",
            "errors": ["All batch prompts failed."],
            "samples": len(prompts),
            "records": records,
        }

    # Aggregate statistics
    total_tokens = sum(token_counts) if token_counts else 0
    total_time = sum(latencies) if latencies else 0.0
    throughput = (total_tokens / total_time) if total_time > 0 else 0.0

    summary = {
        "test": "batch_inference",
        "status": "pass",
        "samples": len(prompts),
        "successful": len(successful),
        "failed": len(prompts) - len(successful),
        "latency_sec": {
            "avg": round(mean(latencies), 4) if latencies else None,
            "median": round(median(latencies), 4) if latencies else None,
            "min": round(min(latencies), 4) if latencies else None,
            "max": round(max(latencies), 4) if latencies else None,
            "sum": round(total_time, 4),
        },
        "tokens_out": {
            "sum": total_tokens,
            "avg": round(mean(token_counts), 2) if token_counts else None,
            "min": min(token_counts) if token_counts else None,
            "max": max(token_counts) if token_counts else None,
        },
        "throughput_tokens_per_sec": round(throughput, 2),
        "generation": {
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        "records": records,
    }

    if verbose:
        print("\n[TEST] Batch Inference Summary")
        print(f"  samples: {summary['samples']}, ok: {summary['successful']}, fail: {summary['failed']}")
        lat = summary["latency_sec"]
        toks = summary["tokens_out"]
        print(f"  latency avg/med/min/max (s): {lat['avg']}/{lat['median']}/{lat['min']}/{lat['max']}")
        print(f"  tokens sum/avg/min/max: {toks['sum']}/{toks['avg']}/{toks['min']}/{toks['max']}")
        print(f"  throughput: {summary['throughput_tokens_per_sec']} tokens/sec")

    return summary
