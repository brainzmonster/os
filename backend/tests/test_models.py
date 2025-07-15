import time
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
