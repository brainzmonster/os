import logging
import time
from datetime import datetime

from backend.core.config import settings
from backend.models.loader import load_model
from backend.db.connection import init_db

logger = logging.getLogger("brainz")


class SyntharaEngine:
    """
    Central bootstrap/coordination engine.
    - Boots DB + model runtime
    - Exposes model and DB handles
    - Tracks boot status and metadata
    """

    def __init__(self):
        self.model = None           # Holds the loaded model bundle (usually {"model": ..., "tokenizer": ...})
        self.model_meta = {}        # Lightweight metadata about the loaded model
        self.db = None              # Database engine/connection handle
        self.boot_time = None       # ISO timestamp when boot() was called
        self.booted = False         # Boot state flag

    def boot(self, dry_run: bool = False, debug_mode: bool = False):
        """
        Initialize DB + model subsystems (unless dry_run).
        Idempotent: will not re-run if already booted.
        """
        if self.booted:
            logger.warning("[brainzOS] Engine already booted. Skipping reinitialization.")
            return

        start = time.time()
        self.boot_time = datetime.utcnow().isoformat()
        logger.info(f"[brainzOS] Boot sequence initiated @ {self.boot_time}")

        if dry_run:
            logger.info("[brainzOS] Dry-run enabled. No subsystems will be loaded.")
            return

        try:
            # 1) Database
            self.db = init_db()
            logger.info("[brainzOS] Database connection initialized.")

            # 2) Model runtime
            self.model = load_model()
            self.model_meta = self._extract_model_metadata(self.model)
            logger.info(f"[brainzOS] Model loaded: {self.model_meta.get('name')}")

            self.booted = True
            duration = round(time.time() - start, 2)
            logger.info(f"[brainzOS] Boot completed in {duration}s.")
        except Exception as e:
            logger.error(f"[brainzOS] Boot failed: {str(e)}")
            self.booted = False

    def get_model(self):
        """
        Return the currently loaded model bundle and its metadata.
        Shape: {"model": <HF model>, "tokenizer": <HF tokenizer>} + separate meta in status().
        """
        return {
            "model": self.model,
            "meta": self.model_meta
        }

    def get_db(self):
        """Return the database engine/connection."""
        return self.db

    def status(self):
        """
        Return a simple status snapshot for health endpoints or diagnostics.
        """
        return {
            "booted": self.booted,
            "boot_time": self.boot_time,
            "model_loaded": self.model is not None,
            "model_name": self.model_meta.get("name", "N/A"),
            "db_connected": self.db is not None,
            "debug_mode": settings.DEBUG
        }

    def shutdown(self):
        """
        Tear down in-memory references (explicit resource cleanup should be handled by respective subsystems).
        """
        logger.info("[brainzOS] Shutting down engine subsystems...")
        self.model = None
        self.model_meta = {}
        self.db = None
        self.booted = False
        logger.info("[brainzOS] Engine shutdown complete.")

    def _extract_model_metadata(self, model_bundle):
        """
        Best-effort metadata extraction that tolerates different loader return shapes.
        - If load_model() returns {"model": ..., "tokenizer": ...}, we introspect the inner model.
        - If a raw model object is returned, we introspect it directly.
        """
        try:
            # Handle dict bundle from loader
            if isinstance(model_bundle, dict) and "model" in model_bundle:
                inner = model_bundle.get("model")
                tokenizer = model_bundle.get("tokenizer", None)
                return {
                    "name": getattr(inner, "name_or_path", "unknown"),
                    "type": type(inner).__name__,
                    "has_tokenizer": tokenizer is not None
                }
            # Fallback: treat as raw model object
            return {
                "name": getattr(model_bundle, "name_or_path", "unknown"),
                "type": type(model_bundle).__name__,
                "has_tokenizer": hasattr(model_bundle, "tokenizer")
            }
        except Exception:
            return {}

    # -------------------------------------------------------------------------
    # NEW: Warmup function to pre-initialize model kernels/caches
    # -------------------------------------------------------------------------
    def warmup_inference(self, prompt: str = "ping", max_tokens: int = 8, temperature: float = 0.0) -> dict:
        """
        Run a tiny inference pass to:
          - Initialize model execution graphs/kernels (helps avoid first-token latency spikes)
          - Validate that the model+tokenizer are usable
          - Return timing + tokenization stats for observability

        Safe no-op if the engine is not fully booted.
        Returns a dict with 'success', 'latency_sec', 'generated_tokens', and 'error' (if any).
        """
        if not self.booted or not self.model:
            msg = "engine not booted or model not loaded"
            logger.warning(f"[brainzOS] warmup skipped: {msg}")
            return {"success": False, "error": msg}

        try:
            import torch  # local import to avoid hard dependency at module import time

            # Support both bundle-dict and raw model forms
            if isinstance(self.model, dict):
                model = self.model.get("model")
                tokenizer = self.model.get("tokenizer")
            else:
                # If a custom loader returned a raw model, we expect an attached tokenizer attribute
                model = self.model
                tokenizer = getattr(self.model, "tokenizer", None)

            if model is None or tokenizer is None:
                msg = "model/tokenizer unavailable for warmup"
                logger.error(f"[brainzOS] warmup failed: {msg}")
                return {"success": False, "error": msg}

            # Tokenize and move to appropriate device
            inputs = tokenizer(prompt, return_tensors="pt")
            device = next(model.parameters()).device if hasattr(model, "parameters") else "cpu"
            inputs = {k: v.to(device) for k, v in inputs.items()}

            start = time.time()
            with torch.no_grad():
                # Minimal generation to touch decode path
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=True if temperature > 0 else False,
                )
            latency = round(time.time() - start, 4)

            # Count tokens of generated piece (best-effort)
            decoded = tokenizer.decode(outputs[0], skip_special_tokens=True)
            gen_len = len(tokenizer.encode(decoded))

            logger.info(f"[brainzOS] warmup OK: {latency}s, tokens={gen_len}")
            return {
                "success": True,
                "latency_sec": latency,
                "generated_tokens": gen_len,
                "sample": decoded[:120]  # short peek to avoid noisy logs
            }
        except Exception as e:
            logger.exception(f"[brainzOS] warmup error: {e}")
            return {"success": False, "error": str(e)}


# Global engine instance
engine = SyntharaEngine()
