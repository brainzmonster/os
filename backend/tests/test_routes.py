"""
FastAPI integration tests for the brainz OS API.

We keep the original tests intact and add:
  - test_system_logs(): validates the logs endpoint with filters/pagination
  - test_user_create(): creates a unique user and verifies API key issuance
  - run_suite(): convenience runner to execute all tests and return a summary

Each test returns a dict so these can be consumed by external CI tooling
without relying on pytest only.
"""

import time
import uuid
from typing import Dict, List

from fastapi.testclient import TestClient
from backend.api.server import app

client = TestClient(app)


def test_root(verbose: bool = True) -> dict:
    """
    Health-check for the root endpoint.
    """
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
    """
    Basic generation path test for /api/llm/query.
    """
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
    """
    Smoke test for /api/llm/train with minimal payload.
    """
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
    """
    Validates that invalid payloads are rejected with 422.
    """
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


# ---------------------------------------------------------------------------
# NEW: Test the system logs endpoint with filtering/pagination parameters
# ---------------------------------------------------------------------------
def test_system_logs(verbose: bool = True) -> dict:
    """
    Calls /api/system/logs with optional filters to ensure the endpoint
    returns a structured payload and respects limit/offset parameters.
    """
    result = {"test": "system_logs", "status": "pass"}
    try:
        params = {
            "limit": 10,
            "offset": 0,
            "level": "INFO",
        }
        res = client.get("/api/system/logs", params=params)
        assert res.status_code == 200

        data = res.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
        assert data["limit"] == params["limit"]
        assert data["offset"] == params["offset"]

        if verbose:
            print(f"[✓] /api/system/logs returned {len(data['logs'])} entries")

        result.update({
            "returned": len(data["logs"]),
            "limit": data["limit"],
            "offset": data["offset"],
        })
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# NEW: Test user creation flow for /api/user/create with a unique username
# ---------------------------------------------------------------------------
def test_user_create(verbose: bool = True) -> dict:
    """
    Creates a unique user and asserts an API key is issued.
    Uses a random suffix to avoid collisions between runs.
    """
    result = {"test": "user_create", "status": "pass"}
    try:
        uname = f"tester_{uuid.uuid4().hex[:8]}"
        payload = {"username": uname}
        res = client.post("/api/user/create", json=payload)
        assert res.status_code == 200

        data = res.json()
        assert data.get("username") == uname
        assert isinstance(data.get("api_key"), str) and len(data["api_key"]) > 0

        if verbose:
            print(f"[✓] /api/user/create created '{uname}'")

        result.update({
            "username": uname,
            "api_key_len": len(data["api_key"]),
        })
    except Exception as e:
        result["status"] = "fail"
        result["error"] = str(e)
    return result


# ---------------------------------------------------------------------------
# NEW: Convenience runner to execute the whole suite and summarize
# ---------------------------------------------------------------------------
def run_suite(verbose: bool = True) -> Dict[str, dict]:
    """
    Run all integration tests in-process and return a summary dict.
    Useful for ad-hoc checks and CI steps that don't use pytest directly.
    """
    tests = [
        test_root,
        test_llm_query,
        test_train_endpoint,
        test_invalid_query_payload,
        test_system_logs,     # NEW
        test_user_create,     # NEW
    ]

    results: List[dict] = []
    for t in tests:
        try:
            results.append(t(verbose=verbose))
        except TypeError:
            # Backwards-compatible with tests that don't accept 'verbose'
            results.append(t())

    summary = {
        "passed": sum(1 for r in results if r.get("status") == "pass"),
        "failed": sum(1 for r in results if r.get("status") == "fail"),
        "results": results,
    }

    if verbose:
        print("\n=== Integration Test Summary ===")
        print(f"Passed: {summary['passed']}  Failed: {summary['failed']}")

    return summary


# Allow running this module directly for a quick local check
if __name__ == "__main__":
    run_suite(verbose=True)
