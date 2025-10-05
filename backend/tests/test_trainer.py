import time
import traceback
from typing import List, Dict

from backend.models.trainer import fine_tune_model
from backend.utils.tokenizer import count_tokens  # Optional if available


# ---------------------------------------------------------------------------
# Helper: token estimation with graceful fallback
# ---------------------------------------------------------------------------
def _estimate_tokens_list(texts: List[str]) -> List[int]:
    """
    Estimate token counts per text using the project tokenizer if available,
    otherwise fall back to a whitespace token approximation.
    """
    estimates = []
    for t in texts:
        try:
            estimates.append(count_tokens(t))  # uses project tokenizer if wired
        except Exception:
            estimates.append(len(t.split()))
    return estimates


# ---------------------------------------------------------------------------
# Existing test: minimal fine-tuning sanity check (kept 1:1 compatible)
# ---------------------------------------------------------------------------
def test_fine_tune_small_prompt(verbose: bool = True) -> dict:
    """
    Smoke-test the fine-tuning pipeline on a tiny prompt set.
    Ensures the returned object looks like a HF model (has .generate()).
    """
    sample_prompts = [
        "Explain what a smart contract is in one sentence.",
        "Define the purpose of a crypto wallet.",
        "What is the difference between proof of stake and proof of work?",
    ]

    token_counts = _estimate_tokens_list(sample_prompts)

    if verbose:
        print(f"[TEST] Token counts per prompt: {token_counts}")
        print(f"[TEST] Starting fine-tuning on {len(sample_prompts)} prompts...")

    try:
        start = time.time()
        model = fine_tune_model(sample_prompts)
        end = time.time()

        assert model is not None, "Returned model is None"
        assert hasattr(model, "generate"), "Returned object lacks .generate() method"

        duration = round(end - start, 2)
        print(f"[TEST] Fine-tuning completed in {duration}s")

        return {
            "status": "pass",
            "samples": len(sample_prompts),
            "token_total": sum(token_counts),
            "duration_sec": duration,
        }

    except Exception as e:
        print(f"[TEST] Fine-tuning failed: {e}")
        print(traceback.format_exc())

        return {
            "status": "fail",
            "samples": len(sample_prompts),
            "error": str(e),
            "trace": traceback.format_exc(),
        }


# ---------------------------------------------------------------------------
# NEW: Fine-tune with basic preprocessing (dedup + short prompt filter)
# ---------------------------------------------------------------------------
def test_fine_tune_with_preprocessing(
    verbose: bool = True,
    min_words: int = 4,
    deduplicate: bool = True,
) -> Dict[str, object]:
    """
    Extended validation that emulates a realistic pre-processing step
    BEFORE calling the core trainer:

      - Filters out extremely short prompts (noise)
      - Deduplicates identical prompts (saves time/tokens)
      - Provides detailed accounting (kept vs. dropped)

    This does NOT change the trainer; it simply ensures that upstream
    data prep interops cleanly with the existing fine_tune_model().
    """
    raw_prompts = [
        "Smart contract?",
        "Explain smart contracts on Ethereum in one sentence.",
        "What is a crypto wallet?",
        "What is a crypto wallet?",  # duplicate on purpose
        "Define MEV",
        "Define MEV in the context of Ethereum validators.",
    ]

    # 1) Normalize and filter by min word count
    filtered = [p for p in raw_prompts if len(p.split()) >= min_words]

    # 2) Optional deduplication
    if deduplicate:
        seen = set()
        deduped = []
        for p in filtered:
            if p not in seen:
                deduped.append(p)
                seen.add(p)
        filtered = deduped

    dropped = [p for p in raw_prompts if p not in filtered]
    token_counts = _estimate_tokens_list(filtered)

    if verbose:
        print(f"[TEST] Raw prompts: {len(raw_prompts)}")
        print(f"[TEST] Kept after filtering (min_words={min_words}, dedup={deduplicate}): {len(filtered)}")
        if dropped:
            print(f"[TEST] Dropped ({len(dropped)}): {dropped}")
        print(f"[TEST] Token counts (kept): {token_counts}")

    if not filtered:
        # Nothing to train on — treat as a graceful skip (not a hard failure)
        return {
            "status": "skip",
            "reason": "no_prompts_after_filtering",
            "raw": len(raw_prompts),
            "kept": 0,
            "dropped": len(dropped),
        }

    # 3) Train on the preprocessed prompts
    try:
        start = time.time()
        model = fine_tune_model(filtered)
        end = time.time()

        assert model is not None, "Returned model is None"
        assert hasattr(model, "generate"), "Returned object lacks .generate() method"

        return {
            "status": "pass",
            "raw": len(raw_prompts),
            "kept": len(filtered),
            "dropped": len(dropped),
            "token_total": sum(token_counts),
            "duration_sec": round(end - start, 2),
        }
    except Exception as e:
        print(f"[TEST] Preprocessed fine-tuning failed: {e}")
        print(traceback.format_exc())
        return {
            "status": "fail",
            "error": str(e),
            "trace": traceback.format_exc(),
            "raw": len(raw_prompts),
            "kept": len(filtered),
            "dropped": len(dropped),
        }


# Optional: run locally without pytest to see quick diagnostics
if __name__ == "__main__":
    print(test_fine_tune_small_prompt(verbose=True))
    print(test_fine_tune_with_preprocessing(verbose=True))
