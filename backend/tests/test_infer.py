import time
from backend.models.infer import generate_response
from backend.utils.tokenizer import count_tokens  # Optional


# --------------------------------------------------------------------------
# Extended unit test for validating brainz inference (baseline happy-path)
# --------------------------------------------------------------------------
def test_infer_basic(verbose: bool = True, max_tokens: int = 100) -> dict:
    """
    Smoke-test the inference path with a single prompt.
    Verifies:
      - Output type (string)
      - Output non-emptiness
      - Basic timing + token estimation
    """
    prompt = "Explain the function of a smart contract."

    if verbose:
        print(f"[TEST] Prompt: {prompt}")
        print(f"[TEST] max_tokens = {max_tokens}")

    try:
        start = time.time()
        result = generate_response(prompt, max_tokens=max_tokens)
        end = time.time()

        assert isinstance(result, str), "Output is not a string"
        assert len(result.strip()) > 0, "Output is empty or whitespace"

        # Use brainz tokenizer if available; otherwise fallback to word-count
        token_estimate = (
            count_tokens(result) if "count_tokens" in globals() else len(result.split())
        )

        if verbose:
            print(f"[TEST] Output: {result[:200]}{'...' if len(result) > 200 else ''}")
            print(f"[TEST] Output token estimate: {token_estimate}")
            print(f"[TEST] Inference time: {round(end - start, 3)}s")

        return {
            "status": "pass",
            "prompt": prompt,
            "output": result,
            "tokens_out": token_estimate,
            "duration": round(end - start, 3),
        }

    except Exception as e:
        return {
            "status": "fail",
            "error": str(e),
            "prompt": prompt,
        }


# --------------------------------------------------------------------------
# NEW: Test inference with a system prompt + hard cap on max tokens
# --------------------------------------------------------------------------
def test_infer_with_system_prompt(
    prompt: str = "List three properties of zero-knowledge proofs.",
    system_prompt: str = "You are a precise crypto research assistant. Answer concisely.",
    max_tokens: int = 64,
    temperature: float = 0.2,
    verbose: bool = True,
) -> dict:
    """
    Validates that:
      - System prompt injection is accepted by the inference pipeline.
      - max_tokens is respected (best-effort—generators may vary slightly).
      - Output is still non-empty and relevant.

    Returns a structured dict suitable for CI logs.
    """
    try:
        start = time.time()
        # Combine system + user prompt at the CLI layer (the API also supports this)
        full_prompt = f"{system_prompt}\n{prompt}"
        out = generate_response(
            prompt=full_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        end = time.time()

        assert isinstance(out, str), "Output is not a string"
        assert out.strip(), "Output is empty"

        # Estimate tokens to sanity-check the cap
        tokens_out = count_tokens(out) if "count_tokens" in globals() else len(out.split())
        # Allow a small buffer since HF generation can slightly fluctuate
        cap_ok = tokens_out <= max_tokens * 1.15

        if verbose:
            print("\n[TEST] System-Prompt Inference")
            print(f"[TEST] System Prompt: {system_prompt}")
            print(f"[TEST] User Prompt   : {prompt}")
            print(f"[TEST] max_tokens    : {max_tokens}")
            print(f"[TEST] temperature   : {temperature}")
            print(f"[TEST] duration      : {round(end - start, 3)}s")
            print(f"[TEST] tokens_out    : {tokens_out} (<= ~{int(max_tokens*1.15)} ? {cap_ok})")
            print(f"[TEST] Output        : {out[:240]}{'...' if len(out) > 240 else ''}")

        return {
            "status": "pass" if cap_ok else "warn",
            "cap_respected": cap_ok,
            "duration": round(end - start, 3),
            "tokens_out": tokens_out,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "output": out,
        }

    except Exception as e:
        return {"status": "fail", "error": str(e)}


# --------------------------------------------------------------------------
# NEW: Latency budget check for CI (useful for performance regressions)
# --------------------------------------------------------------------------
def test_infer_latency_budget(
    prompt: str = "Give a one-sentence definition of Solana.",
    budget_ms: int = 2500,
    max_tokens: int = 64,
    temperature: float = 0.7,
    verbose: bool = True,
) -> dict:
    """
    Measures end-to-end generation latency and compares it against a soft budget.
    This does NOT fail the pipeline on slight overages by default, but signals it.

    Args:
      prompt       : input query
      budget_ms    : latency budget in milliseconds
      max_tokens   : generation cap
      temperature  : sampling temperature
      verbose      : print details

    Returns:
      dict with 'within_budget' flag + timing metrics
    """
    try:
        start = time.time()
        _ = generate_response(prompt=prompt, max_tokens=max_tokens, temperature=temperature)
        end = time.time()
        dur_ms = int((end - start) * 1000)
        within = dur_ms <= budget_ms

        if verbose:
            print("\n[TEST] Latency Budget Check")
            print(f"[TEST] Prompt     : {prompt}")
            print(f"[TEST] Budget     : {budget_ms} ms")
            print(f"[TEST] Observed   : {dur_ms} ms (within={within})")

        return {
            "status": "pass" if within else "warn",
            "within_budget": within,
            "duration_ms": dur_ms,
            "budget_ms": budget_ms,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

    except Exception as e:
        return {"status": "fail", "error": str(e), "budget_ms": budget_ms}
