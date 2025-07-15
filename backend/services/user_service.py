from sqlalchemy.orm import Session
from backend.db.models import User
from backend.db.connection import get_db
from uuid import uuid4
from datetime import datetime
import logging

logger = logging.getLogger("brainz.user")

# === User Creation ===

def create_user(username: str, email: str = None) -> dict:
    """
    Create a new user with a unique API key. 
    Optionally attach an email for metadata purposes.
    Returns full user metadata.
    """
    db: Session = next(get_db())

    # Check for duplicate
    if db.query(User).filter(User.username == username).first():
        raise ValueError(f"[brainzaOS] Username already exists: {username}")

    api_key = str(uuid4())
    user = User(username=username, api_key=api_key)
    
    if hasattr(User, "email") and email:
        user.email = email

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"[brainzaOS] New user created: {username}")
    return {
        "username": user.username,
        "api_key": user.api_key,
        "created_at": user.created_at.isoformat(),
        "id": user.id,
    }

# === Lookup ===

def get_user_by_key(api_key: str) -> User:
    db: Session = next(get_db())
    return db.query(User).filter(User.api_key == api_key).first()

def get_user_by_name(username: str) -> User:
    db: Session = next(get_db())
    return db.query(User).filter(User.username == username).first()

# === Utilities ===

def regenerate_api_key(user_id: int) -> str:
    """
    Generates a new API key for the given user ID.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"[brainzaOS] No user found with ID: {user_id}")

    user.api_key = str(uuid4())
    user.updated_at = datetime.utcnow()
    db.commit()
    return user.api_key

def soft_delete_user(user_id: int) -> bool:
    """
    Mark a user as deleted without removing from DB.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = False
        user.is_deleted = True
        user.updated_at = datetime.utcnow()
        db.commit()
        return True
    return False

def get_active_users(limit: int = 100) -> list[User]:
    """
    Return all active users, up to a specified limit.
    """
    db: Session = next(get_db())
    return db.query(User).filter(User.is_active == True).limit(limit).all()
