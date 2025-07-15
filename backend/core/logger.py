import logging
import sys
import os
from logging.handlers import TimedRotatingFileHandler
from backend.utils.logger_store import log_message
from backend.core.config import settings
from datetime import datetime

# Ensure log directory exists
LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# Global logger
logger = logging.getLogger("brainz")
logger.setLevel(logging.DEBUG if settings.DEBUG else getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

# === FORMATTERS ===
default_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
json_format = '{"time": "%(asctime)s", "level": "%(levelname)s", "msg": "%(message)s"}'

formatter = logging.Formatter(default_format)
json_formatter = logging.Formatter(json_format)

# === HANDLERS ===

# Console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logger.level)
console_handler.setFormatter(formatter)

# Rotating file handler (daily rotation, keeps 7 days)
file_handler = TimedRotatingFileHandler(
    filename=os.path.join(LOG_DIR, "brainz.log"),
    when="midnight",
    interval=1,
    backupCount=7,
    encoding="utf-8"
)
file_handler.setLevel(logger.level)
file_handler.setFormatter(formatter)

# In-memory handler for real-time UI/DB feedback
class MemoryLogHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        log_message(msg)

memory_handler = MemoryLogHandler()
memory_handler.setLevel(logger.level)
memory_handler.setFormatter(formatter)

# === ATTACH HANDLERS ===
if not logger.handlers:
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(memory_handler)

# === OPTIONAL JSON LOGGING MODE (switchable) ===
def enable_json_logs():
    console_handler.setFormatter(json_formatter)
    file_handler.setFormatter(json_formatter)
    memory_handler.setFormatter(json_formatter)

def disable_json_logs():
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    memory_handler.setFormatter(formatter)

# === RUNTIME CONTEXT LOG ===
logger.info(f"brainz logger initialized @ {datetime.utcnow().isoformat()}")
logger.info(f"Logging level: {logging.getLevelName(logger.level)}")
logger.info(f"Log file: {file_handler.baseFilename}")
