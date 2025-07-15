from backend.core.registry import registry
from backend.core.config import settings
import traceback

# Extended test for registry behavior
def test_registry(verbose: bool = True) -> dict:
    results = {"test": "registry", "status": "pass", "errors": []}

    try:
        if verbose: print("[TEST] Registering 'test-key' with int value...")
        registry.register("test-key", 123)
        assert registry.exists("test-key")
        assert registry.get("test-key") == 123

        if verbose: print("[TEST] Overwriting 'test-key' with string...")
        registry.register("test-key", "updated")
        assert registry.get("test-key") == "updated"

        if verbose: print("[TEST] Registering multiple values...")
        registry.register("another-key", [1, 2, 3])
        assert isinstance(registry.get("another-key"), list)

        if verbose: print("[TEST] Clearing registry...")
        registry.clear()
        assert not registry.exists("test-key")
        assert not registry.exists("another-key")

    except Exception as e:
        results["status"] = "fail"
        results["errors"].append(str(e))
        results["trace"] = traceback.format_exc()

    return results

# Extended test for system config settings
def test_settings(verbose: bool = True) -> dict:
    results = {"test": "settings", "status": "pass", "errors": []}

    try:
        if verbose: print(f"[TEST] PROJECT_NAME = {settings.PROJECT_NAME}")
        assert isinstance(settings.PROJECT_NAME, str)

        if verbose: print(f"[TEST] DEBUG = {settings.DEBUG}")
        assert isinstance(settings.DEBUG, bool)

        if verbose: print(f"[TEST] MODEL_NAME = {settings.MODEL_NAME}")
        assert isinstance(settings.MODEL_NAME, str)

        if verbose: print(f"[TEST] DATABASE_URL = {settings.DATABASE_URL}")
        assert settings.DATABASE_URL.startswith("postgresql")

        if verbose: print(f"[TEST] TEMPERATURE = {settings.TEMPERATURE}")
        assert 0.0 <= settings.TEMPERATURE <= 2.0

        if verbose: print(f"[TEST] MAX_TOKENS = {settings.MAX_TOKENS}")
        assert isinstance(settings.MAX_TOKENS, int)
        assert settings.MAX_TOKENS > 0

    except Exception as e:
        results["status"] = "fail"
        results["errors"].append(str(e))
        results["trace"] = traceback.format_exc()

    return results
