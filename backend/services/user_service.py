from sqlalchemy.orm import Session
from backend.db.models import User
from backend.db.connection import get_db
from uuid import uuid4
from datetime import datetime
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("brainz.user")


# ======================================================================
# User Creation
# ======================================================================

def create_user(username: str, email: str = None) -> dict:
    """
    Create a new user with a unique API key.
    Optionally attach an email for metadata purposes.
    Returns full user metadata.

    NOTE: This is strict and will raise if the username already exists.
    Use `ensure_user` below if you want idempotent behavior.
    """
    db: Session = next(get_db())

    # Check for duplicate usernames (unique constraint)
    if db.query(User).filter(User.username == username).first():
        # keep message wording stable to existing logs
        raise ValueError(f"[brainzaOS] Username already exists: {username}")

    api_key = str(uuid4())
    user = User(username=username, api_key=api_key)

    # Attach email if the schema supports it
    if hasattr(User, "email") and email:
        user.email = email

    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info(f"[brainzaOS] New user created: {username}")
    return {
        "username": user.username,
        "api_key": user.api_key,
        "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        "id": user.id,
    }


# ======================================================================
# NEW: Idempotent creation helper
# ======================================================================

def ensure_user(username: str, email: Optional[str] = None) -> Dict[str, Any]:
    """
    Idempotent user provisioning:
      - If the user exists (optionally inactive), return its metadata.
      - If not, create a fresh user (with email if supported).

    This is useful for scripts/agents that should not fail when a user
    is already present. It preserves the existing `create_user` behavior
    by NOT modifying that function.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.username == username).first()

    if user:
        # Optionally (and safely) attach email on existing user if the column exists and is empty
        if hasattr(User, "email") and email and not getattr(user, "email", None):
            user.email = email
            user.updated_at = datetime.utcnow() if hasattr(User, "updated_at") else None
            db.commit()
            db.refresh(user)

        logger.info(f"[brainzOS] ensure_user: existing user '{username}' returned")
        return {
            "username": user.username,
            "api_key": user.api_key,
            "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
            "id": user.id,
            "was_created": False,
        }

    # If not present, delegate to strict create
    created = create_user(username=username, email=email)
    created["was_created"] = True
    logger.info(f"[brainzOS] ensure_user: created new user '{username}'")
    return created


# ======================================================================
# Lookup
# ======================================================================

def get_user_by_key(api_key: str) -> User:
    db: Session = next(get_db())
    return db.query(User).filter(User.api_key == api_key).first()


def get_user_by_name(username: str) -> User:
    db: Session = next(get_db())
    return db.query(User).filter(User.username == username).first()


# ======================================================================
# NEW: API key validation utility
# ======================================================================

def validate_api_key(api_key: str, require_active: bool = True) -> Dict[str, Any]:
    """
    Validate an API key and (optionally) the active status of its owner.

    Returns a dict:
      {
        "valid": bool,
        "reason": Optional[str],     # present if valid=False
        "user": Optional[dict]       # minimal user metadata if valid=True
      }

    This helper keeps callers simple and avoids repeating DB checks.
    It does NOT mutate any state.
    """
    user = get_user_by_key(api_key)
    if not user:
        return {"valid": False, "reason": "not_found", "user": None}

    if require_active and hasattr(User, "is_active") and not getattr(user, "is_active", True):
        return {"valid": False, "reason": "inactive", "user": None}

    return {
        "valid": True,
        "reason": None,
        "user": {
            "id": user.id,
            "username": user.username,
            "created_at": user.created_at.isoformat() if getattr(user, "created_at", None) else None,
        },
    }


# ======================================================================
# Utilities
# ======================================================================

def regenerate_api_key(user_id: int) -> str:
    """
    Generates a new API key for the given user ID.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        # keep message wording stable
        raise ValueError(f"[brainzaOS] No user found with ID: {user_id}")

    user.api_key = str(uuid4())
    if hasattr(User, "updated_at"):
        user.updated_at = datetime.utcnow()
    db.commit()
    return user.api_key


def soft_delete_user(user_id: int) -> bool:
    """
    Mark a user as deleted without removing from DB.
    Requires the model to have `is_active` and `is_deleted` flags.
    """
    db: Session = next(get_db())
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if hasattr(User, "is_active"):
            user.is_active = False
        if hasattr(User, "is_deleted"):
            user.is_deleted = True
        if hasattr(User, "updated_at"):
            user.updated_at = datetime.utcnow()
        db.commit()
        return True
    return False


def get_active_users(limit: int = 100) -> list[User]:
    """
    Return all active users, up to a specified limit.
    If the model lacks `is_active`, all users are considered active.
    """
    db: Session = next(get_db())
    if hasattr(User, "is_active"):
        return db.query(User).filter(User.is_active == True).limit(limit).all()
    # Fallback: return the latest users if no 'is_active' flag exists
    return db.query(User).order_by(User.created_at.desc() if hasattr(User, "created_at") else User.id.desc()).limit(limit).all()
