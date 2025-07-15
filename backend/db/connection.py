import os
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
from contextlib import contextmanager
from datetime import datetime

# Read DB URL from environment
DB_URL = os.getenv("DATABASE_URL", "postgresql://brainz:synthpass@localhost/brainzdb")
ECHO_SQL = os.getenv("DB_ECHO", "false").lower() == "true"

# Configure engine with optional echo and connection pooling
engine = create_engine(
    DB_URL,
    echo=ECHO_SQL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

# ORM base
Base = declarative_base()

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger("brainz.db")

# Initialize database (used during boot or setup)
def init_db(retry: bool = True):
    try:
        Base.metadata.create_all(bind=engine)
        logger.info(f"[{datetime.utcnow().isoformat()}] [✓] Database initialized.")
    except OperationalError as e:
        logger.error(f"[✗] Database init failed: {e}")
        if retry:
            logger.info("[~] Retrying connection in 3s...")
            import time
            time.sleep(3)
            Base.metadata.create_all(bind=engine)
    return engine

# Health check utility
def check_db_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[✓] DB connection healthy")
        return True
    except Exception as e:
        logger.warning(f"[!] DB connection failed: {e}")
        return False

# DB schema reflection (e.g. for Alembic or inspection)
def reflect_schema():
    return Base.metadata

# FastAPI dependency wrapper
@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Inspect available tables and columns
def get_db_structure() -> dict:
    inspector = inspect(engine)
    structure = {}
    for table in inspector.get_table_names():
        columns = inspector.get_columns(table)
        structure[table] = [col['name'] for col in columns]
    return structure
