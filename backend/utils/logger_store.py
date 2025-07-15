import logging
from datetime import datetime

# In-memory log buffer
LOG_STORE = []
LOG_STORE_MAX_SIZE = 1000  # Auto-trim when exceeding this

LOG_LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50
}

# Add a log entry with optional level and source
def add_log(record: str, level: str = "INFO", source: str = "core"):
    level = level.upper()
    timestamp = datetime.utcnow().isoformat()

    LOG_STORE.append({
        "timestamp": timestamp,
        "level": level,
        "source": source,
        "message": record
    })

    # Trim old logs to prevent unbounded memory growth
    if len(LOG_STORE) > LOG_STORE_MAX_SIZE:
        LOG_STORE[:] = LOG_STORE[-LOG_STORE_MAX_SIZE:]


# Retrieve logs with optional filtering and pagination
def get_logs(limit: int = 50, level: str = None, offset: int = 0, source: str = None) -> list:
    logs = LOG_STORE

    # Filter by level (inclusive >=)
    if level and level.upper() in LOG_LEVELS:
        min_level = LOG_LEVELS[level.upper()]
        logs = [log for log in logs if LOG_LEVELS.get(log["level"], 0) >= min_level]

    # Filter by source module
    if source:
        logs = [log for log in logs if log["source"] == source]

    # Apply pagination
    start = max(0, len(logs) - limit - offset)
    end = len(logs) - offset if offset < len(logs) else len(logs)
    return logs[start:end]
