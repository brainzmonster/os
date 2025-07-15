import time
from backend.models.infer import generate_response
from backend.utils.tokenizer import count_tokens  # Optional

# Extended unit test for validating brainz inference
def test_infer_basic(verbose: bool = True, max_tokens: int = 100) -> dict:
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

        token_estimate = count_tokens(result) if "count_tokens" in globals() else len(result.split())

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
