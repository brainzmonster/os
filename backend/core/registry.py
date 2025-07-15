import time
import json
from typing import Any, Dict, List, Optional


class brainzRegistry:
    def __init__(self):
        # Each key maps to a dict with value + metadata
        self._registry: Dict[str, Dict[str, Any]] = {}

    def register(self, key: str, value: Any, ttl: Optional[int] = None, lock: bool = False):
        """Register a key-value pair with optional TTL (in seconds) and lock flag"""
        if key in self._registry and self._registry[key].get("locked"):
            raise ValueError(f"Key '{key}' is locked and cannot be overwritten.")

        self._registry[key] = {
            "value": value,
            "timestamp": time.time(),
            "ttl": ttl,
            "locked": lock
        }

    def get(self, key: str) -> Any:
        """Retrieve a value by key if it exists and is not expired"""
        entry = self._registry.get(key)
        if not entry:
            return None

        # Check TTL expiry
        if entry.get("ttl") is not None:
            if time.time() - entry["timestamp"] > entry["ttl"]:
                self.unregister(key)
                return None

        return entry["value"]

    def exists(self, key: str) -> bool:
        """Check if key exists and is valid"""
        return self.get(key) is not None

    def unregister(self, key: str):
        """Remove key unless it is locked"""
        if key in self._registry:
            if self._registry[key].get("locked"):
                raise ValueError(f"Key '{key}' is locked and cannot be removed.")
            del self._registry[key]

    def clear(self, force: bool = False):
        """Clear all keys, except locked unless force=True"""
        keys = list(self._registry.keys())
        for key in keys:
            if not self._registry[key].get("locked") or force:
                del self._registry[key]

    def list_keys(self, include_locked: bool = True) -> List[str]:
        """Return all active keys (optionally include locked)"""
        return [
            k for k in self._registry
            if include_locked or not self._registry[k].get("locked")
        ]

    def export_json(self) -> str:
        """Export the registry as a JSON string (without TTL expiration check)"""
        return json.dumps(self._registry, default=str, indent=2)

    def import_json(self, json_string: str):
        """Restore registry state from a JSON string (for debugging/dev only)"""
        data = json.loads(json_string)
        if not isinstance(data, dict):
            raise ValueError("Invalid registry JSON format.")
        self._registry = data

    def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve metadata for a given key"""
        if key not in self._registry:
            return None
        meta = self._registry[key].copy()
        meta.pop("value", None)
        return meta


# Global instance of the registry
registry = brainzRegistry()
