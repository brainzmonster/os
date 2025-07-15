from fastapi.testclient import TestClient
from backend.api.server import app
import time

client = TestClient(app)

def test_root(verbose: bool = True) -> dict:
    result = {"test": "root", "status": "pass"}
    try:
        res = client.get("/")
        assert res.status_code == 200
        assert res.json() == {"message": "brainz OS is running."}
        if verbose:
            print("[✓] / endpoint OK")
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    return result

def test_llm_query(verbose: bool = True) -> dict:
    result = {"test": "llm_query", "status": "pass"}
    payload = {
        "input": "What is Web3?",
        "max_tokens": 50,
        "temperature": 0.5
    }

    try:
        start = time.time()
        res = client.post("/api/llm/query", json=payload)
        duration = round(time.time() - start, 3)
        data = res.json()

        assert res.status_code == 200
        assert "response" in data
        assert isinstance(data["response"], str)
        assert len(data["response"].strip()) > 0

        if verbose:
            print(f"[✓] /api/llm/query responded in {duration}s")
            print(f"[Preview] {data['response'][:120]}{'...' if len(data['response']) > 120 else ''}")

        result["latency"] = duration
        result["output_length"] = len(data["response"])

    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)

    return result

def test_train_endpoint(verbose: bool = True) -> dict:
    result = {"test": "llm_train", "status": "pass"}
    try:
        payload = {
            "texts": ["Define blockchain in one line.", "What is a DAO?"]
        }

        res = client.post("/api/llm/train", json=payload)
        data = res.json()

        assert res.status_code == 200
        assert data.get("status") == "success"

        if verbose:
            print("[✓] /api/llm/train accepted training payload")

    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)

    return result

def test_invalid_query_payload(verbose: bool = True) -> dict:
    result = {"test": "llm_query_invalid", "status": "pass"}
    try:
        res = client.post("/api/llm/query", json={"wrong_field": "oops"})
        assert res.status_code == 422  # Unprocessable Entity
        if verbose:
            print("[✓] /api/llm/query rejected bad payload as expected")
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    return result
