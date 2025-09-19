import os
import uuid
import json
import secrets
import logging
from datetime import datetime
from typing import Optional, Tuple, List

from sqlalchemy.orm import Session
from backend.db.connection import init_db
from backend.db.schema import reflect_schema
from backend.db.models import User

# ---------------------------------------------------------------------------
# Utility: generate a cryptographically strong API key
# ---------------------------------------------------------------------------
def generate_api_key(n_bytes: int = 32) -> str:
    """
    Generate a secure API key using os.urandom/secrets.
    Default size is 32 bytes -> 64 hex chars.
    """
    return secrets.token_hex(n_bytes)

# ---------------------------------------------------------------------------
# Optional: seed a single default user (idempotent)
# ---------------------------------------------------------------------------
def seed_default_user(session: Session, username: str, api_key: str) -> bool:
    """
    Create a single default user if it doesn't already exist.
    Returns True if a new user was created, False if it already existed.
    """
    if not session.query(User).filter_by(username=username).first():
        session.add(User(username=username, api_key=api_key))
        session.commit()
        return True
    return False

# ---------------------------------------------------------------------------
# NEW: bulk seeding helper from a JSON/JSONL file (idempotent)
# ---------------------------------------------------------------------------
def seed_users_from_file(session: Session, file_path: str) -> Tuple[int, int, List[str]]:
    """
    Seed multiple users from a file. Supports:
      - JSON array: [{"username": "...", "api_key": "..."}, ...]
      - JSON Lines: one JSON object per line
    Missing api_key entries will be auto-generated.
    Returns (created_count, skipped_count, errors)
    """
    created = 0
    skipped = 0
    errors: List[str] = []

    if not os.path.isfile(file_path):
        return (0, 0, [f"Seed file not found: {file_path}"])

    # Try JSON array first; if that fails, try JSONL line-by-line
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    data = [data]
                if not isinstance(data, list):
                    raise ValueError("Seed file must be a JSON array or JSONL")
                records = data
            except json.JSONDecodeError:
                # JSONL fallback
                f.seek(0)
                records = []
                for i, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        records.append(obj)
                    except Exception as e:
                        errors.append(f"Line {i}: {e}")

        for obj in records:
            username = (obj.get("username") or "").strip()
            api_key = (obj.get("api_key") or "").strip() or generate_api_key()

            if not username:
                errors.append("Missing username in record; skipped.")
                continue

            if session.query(User).filter_by(username=username).first():
                skipped += 1
                continue

            session.add(User(username=username, api_key=api_key))
            created += 1

        session.commit()
    except Exception as e:
        errors.append(str(e))

    return (created, skipped, errors)

# ---------------------------------------------------------------------------
# NEW: rotate admin key (opt-in via env)
# ---------------------------------------------------------------------------
def rotate_admin_key(session: Session, username: str, new_key: Optional[str] = None) -> bool:
    """
    Rotate the API key for a given admin user if it exists.
    Returns True if rotated, False if user not found.
    """
    user = session.query(User).filter_by(username=username).first()
    if not user:
        return False
    user.api_key = new_key or generate_api_key()
    session.commit()
    return True

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
def main():
    # Session + logging setup
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("brainzDB")

    logger.info(f"[{session_id}] Starting brainzOS database initialization...")

    try:
        # Initialize engine and create tables (no-op if already present)
        engine = init_db()
        reflect_schema().create_all(bind=engine)
        logger.info(f"[{session_id}] Tables created or already exist.")

        # Check if seeding is globally skipped
        if os.getenv("SKIP_DB_SEEDING", "false").lower() == "true":
            logger.info(f"[{session_id}] Skipping seeding step due to environment flag.")
            print("\n[✓] Database initialized (seeding skipped by flag).")
            print(f"[✓] Session ID: {session_id}")
            print(f"[✓] Timestamp: {timestamp}")
            return

        # Open DB session
        session = Session(bind=engine)

        # -------------------------------------------------------------------
        # Admin user seeding (idempotent)
        # - ADMIN_KEY_AUTO=true → ignore ADMIN_KEY and auto-generate
        # - otherwise use ADMIN_KEY or default 'root-dev-key'
        # -------------------------------------------------------------------
        username = os.getenv("ADMIN_USER", "admin")
        if os.getenv("ADMIN_KEY_AUTO", "false").lower() == "true":
            api_key = generate_api_key()
        else:
            api_key = os.getenv("ADMIN_KEY", "root-dev-key")

        seeded = seed_default_user(session, username, api_key)
        if seeded:
            logger.info(f"[{session_id}] Admin user '{username}' seeded successfully.")
        else:
            logger.info(f"[{session_id}] Admin user '{username}' already exists.")

        # -------------------------------------------------------------------
        # NEW: optional bulk user seeding from file
        # BRAINS_SEED_USERS_FILE=/path/to/users.json|jsonl
        # -------------------------------------------------------------------
        seed_file = os.getenv("BRAINS_SEED_USERS_FILE", "").strip()
        if seed_file:
            logger.info(f"[{session_id}] Bulk seeding users from file: {seed_file}")
            created, skipped, errs = seed_users_from_file(session, seed_file)
            if created or skipped:
                logger.info(f"[{session_id}] Bulk seeding summary - created: {created}, skipped: {skipped}")
            if errs:
                for e in errs:
                    logger.warning(f"[{session_id}] Bulk seeding issue: {e}")

        # -------------------------------------------------------------------
        # NEW: optional admin key rotation (one-shot)
        # ROTATE_ADMIN_KEY=true → rotate 'ADMIN_USER' key
        # ROTATE_ADMIN_KEY_VALUE=<explicit_key> (optional)
        # -------------------------------------------------------------------
        if os.getenv("ROTATE_ADMIN_KEY", "false").lower() == "true":
            new_key_env = os.getenv("ROTATE_ADMIN_KEY_VALUE")
            rotated = rotate_admin_key(session, username=username, new_key=new_key_env)
            if rotated:
                logger.info(f"[{session_id}] Admin key rotated for '{username}'.")
            else:
                logger.info(f"[{session_id}] Admin key rotation skipped (user not found).")

        # Close session
        session.close()

        # Final output
        print("\n[✓] Database initialized.")
        print(f"[✓] Session ID: {session_id}")
        print(f"[✓] Timestamp: {timestamp}")
        if seeded:
            print(f"[✓] Admin user '{username}' seeded.")
        else:
            print(f"[i] Admin user '{username}' already present. Skipped.")
        if seed_file:
            print(f"[i] Bulk seeding file processed: {seed_file}")
        if os.getenv("ROTATE_ADMIN_KEY", "false").lower() == "true":
            print(f"[i] Admin key rotation attempted for '{username}'.")

    except Exception as e:
        logger.error(f"[{session_id}] Initialization failed: {e}")
        print(f"[✗] DB init failed: {e}")

if __name__ == "__main__":
    main()
