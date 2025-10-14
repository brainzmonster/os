import os
import time
import logging
from typing import Any, Dict, Iterable, List, Optional
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError, SQLAlchemyError

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

# Read DB URL from environment (PostgreSQL by default)
DB_URL = os.getenv("DATABASE_URL", "postgresql://brainz:synthpass@localhost/brainzdb")

# Verbose SQL echo for debugging
ECHO_SQL = os.getenv("DB_ECHO", "false").lower() == "true"

# Pool configuration (overridable via env)
POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "10"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "20"))
POOL_PRE_PING = os.getenv("DB_POOL_PRE_PING", "true").lower() == "true"

# -----------------------------------------------------------------------------
# Engine / Session setup
# -----------------------------------------------------------------------------

# Configure engine with optional echo and connection pooling
engine = create_engine(
    DB_URL,
    echo=ECHO_SQL,
    pool_pre_ping=POOL_PRE_PING,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
)

# ORM base
Base = declarative_base()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger("brainz.db")


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------

def _redact_url(url: str) -> str:
    """
    Redact credentials in a DB URL for safe logging.
    Example: postgresql://user:****@host/db
    """
    try:
        if "@" in url and "://" in url:
            head, tail = url.split("://", 1)
            creds_host = tail.split("@", 1)
            if len(creds_host) == 2:
                creds, host = creds_host
                if ":" in creds:
                    user, _ = creds.split(":", 1)
                    return f"{head}://{user}:****@{host}"
        return url
    except Exception:
        return "****"


# -----------------------------------------------------------------------------
# Initialization / Health
# -----------------------------------------------------------------------------

def init_db(retry: bool = True):
    """
    Create all tables registered on Base.metadata.
    Retries once on OperationalError (useful on cold boots where DB needs a second).
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"[{datetime.utcnow().isoformat()}] [✓] Database initialized.")
    except OperationalError as e:
        logger.error(f"[✗] Database init failed: {e}")
        if retry:
            logger.info("[~] Retrying connection in 3s...")
            time.sleep(3)
            Base.metadata.create_all(bind=engine)
    return engine


def check_db_connection() -> bool:
    """
    Simple health check by executing a no-op query.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[✓] DB connection healthy")
        return True
    except Exception as e:
        logger.warning(f"[!] DB connection failed: {e}")
        return False


def measure_db_latency(rounds: int = 3) -> float:
    """
    NEW: Measure average DB round-trip latency by executing SELECT 1 a few times.

    Returns:
        float: average latency in milliseconds (ms). Returns -1 on failure.
    """
    timings: List[float] = []
    try:
        with engine.connect() as conn:
            for _ in range(max(1, rounds)):
                t0 = time.perf_counter()
                conn.execute(text("SELECT 1"))
                timings.append((time.perf_counter() - t0) * 1000.0)
        avg = sum(timings) / len(timings)
        logger.info(f"[✓] DB avg latency: {avg:.2f} ms over {len(timings)} rounds")
        return avg
    except Exception as e:
        logger.warning(f"[!] Failed to measure DB latency: {e}")
        return -1.0


# -----------------------------------------------------------------------------
# Schema / Reflection
# -----------------------------------------------------------------------------

def reflect_schema():
    """
    Expose metadata for external tools (e.g., Alembic).
    """
    return Base.metadata


def get_db_structure() -> dict:
    """
    Inspect available tables and columns for diagnostics.
    """
    inspector = inspect(engine)
    structure = {}
    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        structure[table] = [col["name"] for col in columns]
    return structure


# -----------------------------------------------------------------------------
# Session helpers
# -----------------------------------------------------------------------------

@contextmanager
def get_db():
    """
    FastAPI dependency and general context manager for a scoped session.
    Ensures the session is always closed.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def transaction_context():
    """
    NEW: Context manager that wraps a DB session in a transaction.
    Commits on success, rolls back on exception.
    Usage:
        with transaction_context() as db:
            db.add(obj)
            ...
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# -----------------------------------------------------------------------------
# Runtime reconfiguration
# -----------------------------------------------------------------------------

def reconfigure_engine(db_url: Optional[str] = None, **engine_kwargs) -> None:
    """
    NEW: Recreate the SQLAlchemy engine and session factory at runtime.
    Useful for switching databases (e.g., test/prod) without restarting the process.

    Args:
        db_url: Optional new database URL. Defaults to current DB_URL.
        **engine_kwargs: Any extra kwargs forwarded to create_engine(), allowing
                         overriding pool settings, echo, etc.

    Notes:
        - Disposes existing connections.
        - Updates global 'engine' and 'SessionLocal'.
        - Safe to call multiple times.
    """
    global engine, SessionLocal

    new_url = db_url or DB_URL
    safe_url = _redact_url(new_url)
    logger.info(f"[~] Reconfiguring engine to {safe_url}")

    # Dispose old engine connections
    try:
        engine.dispose()
    except Exception:
        pass

    # Build new engine with overrides (fallback to current defaults)
    new_engine = create_engine(
        new_url,
        echo=engine_kwargs.get("echo", ECHO_SQL),
        pool_pre_ping=engine_kwargs.get("pool_pre_ping", POOL_PRE_PING),
        pool_size=engine_kwargs.get("pool_size", POOL_SIZE),
        max_overflow=engine_kwargs.get("max_overflow", MAX_OVERFLOW),
        **{k: v for k, v in engine_kwargs.items() if k not in {"echo", "pool_pre_ping", "pool_size", "max_overflow"}}
    )

    # Swap globals
    engine = new_engine
    SessionLocal.configure(bind=new_engine)  # rebind existing factory
    logger.info("[✓] Engine reconfigured and session factory rebound.")


# -----------------------------------------------------------------------------
# Raw execution helpers
# -----------------------------------------------------------------------------

def execute_query(sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    NEW: Execute a read-oriented SQL statement and return rows as list of dicts.
    This is handy for admin/diagnostics endpoints without writing ad-hoc ORM.

    Args:
        sql: Raw SQL to execute (parameterized with :name placeholders).
        params: Dict of parameters to bind.

    Returns:
        List[Dict[str, Any]]: Rows as dictionaries (column -> value).
    """
    rows: List[Dict[str, Any]] = []
    with engine.connect() as conn:
        result = conn.execute(text(sql), params or {})
        if result.returns_rows:
            cols = result.keys()
            for r in result:
                rows.append({c: v for c, v in zip(cols, r)})
    return rows


def execute_write(sql: str, params: Optional[Dict[str, Any]] = None) -> int:
    """
    NEW: Execute a write statement (INSERT/UPDATE/DELETE) in a transaction.

    Returns:
        int: rowcount affected (if available), -1 if unknown.
    """
    with transaction_context() as db:
        result = db.execute(text(sql), params or {})
        return int(getattr(result, "rowcount", -1))
