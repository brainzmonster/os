from backend.core.registry import registry
from backend.core.config import settings
import traceback
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, urlunparse


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _sanitize_database_url(db_url: str) -> str:
    """
    Hide credentials in DATABASE_URL while preserving structure.
    e.g. postgresql://user:pass@host:5432/db  ->  postgresql://user:***@host:5432/db
    """
    try:
        parsed = urlparse(db_url)
        if parsed.username or parsed.password:
            # Rebuild netloc with masked password
            user = parsed.username or ""
            pw = "***" if parsed.password else ""
            at = f"{user}:{pw}@" if user or pw else ""
            netloc = f"{at}{parsed.hostname or ''}"
            if parsed.port:
                netloc += f":{parsed.port}"
            return urlunparse(parsed._replace(netloc=netloc))
        return db_url
    except Exception:
        # If parsing fails, just return a coarse mask
        return "postgresql://***:***@***:***/***"


# -----------------------------------------------------------------------------
# Extended test for registry behavior
# -----------------------------------------------------------------------------
def test_registry(verbose: bool = True) -> dict:
    results = {"test": "registry", "status": "pass", "errors": []}

    try:
        if verbose:
            print("[TEST] Registering 'test-key' with int value...")
        registry.register("test-key", 123)
        assert registry.exists("test-key")
        assert registry.get("test-key") == 123

        if verbose:
            print("[TEST] Overwriting 'test-key' with string...")
        registry.register("test-key", "updated")
        assert registry.get("test-key") == "updated"

        if verbose:
            print("[TEST] Registering multiple values...")
        registry.register("another-key", [1, 2, 3])
        assert isinstance(registry.get("another-key"), list)

        if verbose:
            print("[TEST] Clearing registry...")
        registry.clear()
        assert not registry.exists("test-key")
        assert not registry.exists("another-key")

    except Exception as e:
        results["status"] = "fail"
        results["errors"].append(str(e))
        results["trace"] = traceback.format_exc()

    return results


# -----------------------------------------------------------------------------
# Extended test for system config settings
# -----------------------------------------------------------------------------
def test_settings(verbose: bool = True) -> dict:
    results = {"test": "settings", "status": "pass", "errors": []}

    try:
        if verbose:
            print(f"[TEST] PROJECT_NAME = {settings.PROJECT_NAME}")
        assert isinstance(settings.PROJECT_NAME, str)

        if verbose:
            print(f"[TEST] DEBUG = {settings.DEBUG}")
        assert isinstance(settings.DEBUG, bool)

        if verbose:
            print(f"[TEST] MODEL_NAME = {settings.MODEL_NAME}")
        assert isinstance(settings.MODEL_NAME, str)

        if verbose:
            print(f"[TEST] DATABASE_URL = {settings.DATABASE_URL}")
        assert settings.DATABASE_URL.startswith("postgresql")

        if verbose:
            print(f"[TEST] TEMPERATURE = {settings.TEMPERATURE}")
        assert 0.0 <= settings.TEMPERATURE <= 2.0

        if verbose:
            print(f"[TEST] MAX_TOKENS = {settings.MAX_TOKENS}")
        assert isinstance(settings.MAX_TOKENS, int)
        assert settings.MAX_TOKENS > 0

    except Exception as e:
        results["status"] = "fail"
        results["errors"].append(str(e))
        results["trace"] = traceback.format_exc()

    return results


# -----------------------------------------------------------------------------
# NEW: Snapshot current settings (sanitized) for diagnostics & bug reports
# -----------------------------------------------------------------------------
def dump_settings_snapshot(sanitize: bool = True) -> Dict[str, Any]:
    """
    Produce a structured, optionally sanitized snapshot of the active settings.
    Safe to log or return from a diagnostics endpoint.

    Args:
        sanitize: mask sensitive values (e.g., DB password)

    Returns:
        dict with key runtime configuration values
    """
    db_url = settings.DATABASE_URL
    snapshot = {
        "project_name": settings.PROJECT_NAME,
        "version": getattr(settings, "VERSION", "unknown"),
        "model_name": settings.MODEL_NAME,
        "database_url": _sanitize_database_url(db_url) if sanitize else db_url,
        "debug": settings.DEBUG,
        "generation": {
            "max_tokens": settings.MAX_TOKENS,
            "temperature": settings.TEMPERATURE,
        },
    }
    return snapshot


# -----------------------------------------------------------------------------
# NEW: Run full self-check suite and return aggregated result
# -----------------------------------------------------------------------------
def run_selfcheck_suite(verbose: bool = True) -> Dict[str, Any]:
    """
    Execute quick integrity checks for registry and settings, and include a
    sanitized config snapshot. Useful for CLI 'health' commands or /health API.
    """
    results: List[Dict[str, Any]] = []
    overall_status = "pass"

    r1 = test_registry(verbose=verbose)
    results.append(r1)
    if r1.get("status") != "pass":
        overall_status = "fail"

    r2 = test_settings(verbose=verbose)
    results.append(r2)
    if r2.get("status") != "pass":
        overall_status = "fail"

    return {
        "status": overall_status,
        "checks": results,
        "snapshot": dump_settings_snapshot(sanitize=True),
    }
