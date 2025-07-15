import os
import uuid
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from backend.db.connection import init_db
from backend.db.schema import reflect_schema
from backend.db.models import User

# Optional: define future model seeders
def seed_default_user(session: Session, username: str, api_key: str):
    if not session.query(User).filter_by(username=username).first():
        session.add(User(username=username, api_key=api_key))
        session.commit()
        return True
    return False

def main():
    # Session + logging setup
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("brainzDB")

    logger.info(f"[{session_id}] Starting brainzOS database initialization...")

    try:
        # Initialize engine and schema
        engine = init_db()
        reflect_schema().create_all(bind=engine)
        logger.info(f"[{session_id}] Tables created or already exist.")

        # Check if seeding is skipped
        if os.getenv("SKIP_DB_SEEDING", "false").lower() == "true":
            logger.info(f"[{session_id}] Skipping seeding step due to environment flag.")
            return

        # Seed admin user
        username = os.getenv("ADMIN_USER", "admin")
        api_key = os.getenv("ADMIN_KEY", "root-dev-key")

        session = Session(bind=engine)
        seeded = seed_default_user(session, username, api_key)
        session.close()

        if seeded:
            logger.info(f"[{session_id}] Admin user '{username}' seeded successfully.")
        else:
            logger.info(f"[{session_id}] Admin user '{username}' already exists.")

        # Optional: Add more seeders here (roles, settings, etc.)

        print("\n[✓] Database initialized.")
        print(f"[✓] Session ID: {session_id}")
        print(f"[✓] Timestamp: {timestamp}")
        if seeded:
            print(f"[✓] Admin user '{username}' seeded.")
        else:
            print(f"[i] Admin user '{username}' already present. Skipped.")

    except Exception as e:
        logger.error(f"[{session_id}] Initialization failed: {e}")
        print(f"[✗] DB init failed: {e}")


if __name__ == "__main__":
    main()
