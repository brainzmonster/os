import time
import traceback
from backend.models.trainer import fine_tune_model
from backend.utils.tokenizer import count_tokens  # Optional if available

# Extended unit test for validating brainz fine-tuning pipeline
def test_fine_tune_small_prompt(verbose: bool = True) -> dict:
    sample_prompts = [
        "Explain what a smart contract is in one sentence.",
        "Define the purpose of a crypto wallet.",
        "What is the difference between proof of stake and proof of work?",
    ]

    token_counts = [count_tokens(p) if "count_tokens" in globals() else len(p.split()) for p in sample_prompts]

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
