import logging
import time
from datetime import datetime

from backend.core.config import settings
from backend.models.loader import load_model
from backend.db.connection import init_db

logger = logging.getLogger("brainz")


class SyntharaEngine:
    def __init__(self):
        self.model = None
        self.model_meta = {}
        self.db = None
        self.boot_time = None
        self.booted = False

    def boot(self, dry_run: bool = False, debug_mode: bool = False):
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
            self.db = init_db()
            logger.info("[brainzOS] Database connection initialized.")

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
        return {
            "model": self.model,
            "meta": self.model_meta
        }

    def get_db(self):
        return self.db

    def status(self):
        return {
            "booted": self.booted,
            "boot_time": self.boot_time,
            "model_loaded": self.model is not None,
            "model_name": self.model_meta.get("name", "N/A"),
            "db_connected": self.db is not None,
            "debug_mode": settings.DEBUG
        }

    def shutdown(self):
        logger.info("[brainzOS] Shutting down engine subsystems...")
        self.model = None
        self.model_meta = {}
        self.db = None
        self.booted = False
        logger.info("[brainzOS] Engine shutdown complete.")

    def _extract_model_metadata(self, model):
        try:
            return {
                "name": getattr(model, "name_or_path", "unknown"),
                "type": type(model).__name__,
                "has_tokenizer": hasattr(model, "tokenizer")
            }
        except Exception:
            return {}


# Global engine instance
engine = SyntharaEngine()
