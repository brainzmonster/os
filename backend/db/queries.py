from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from backend.db.models import PromptLog, User

# === Prompt Queries ===

def get_all_prompts(db: Session, limit: int = 100, offset: int = 0):
    """
    Get all recent prompts, paginated and sorted.
    """
    return (
        db.query(PromptLog)
        .order_by(PromptLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

def get_prompts_by_user(db: Session, user_id: int, limit: int = 50):
    """
    Get recent prompts by a specific user.
    """
    return (
        db.query(PromptLog)
        .filter(PromptLog.user_id == user_id)
        .order_by(PromptLog.created_at.desc())
        .limit(limit)
        .all()
    )

def get_prompts_by_tag(db: Session, tag: str, limit: int = 50):
    """
    Get prompts with a specific tag label.
    """
    return (
        db.query(PromptLog)
        .filter(PromptLog.tag == tag)
        .order_by(PromptLog.created_at.desc())
        .limit(limit)
        .all()
    )

def search_prompts_by_text(db: Session, substring: str, limit: int = 50):
    """
    Search for prompts containing a specific keyword or phrase.
    """
    return (
        db.query(PromptLog)
        .filter(PromptLog.prompt.ilike(f"%{substring}%"))
        .order_by(PromptLog.created_at.desc())
        .limit(limit)
        .all()
    )

def get_prompt_count(db: Session) -> int:
    """
    Return total number of prompt logs.
    """
    return db.query(func.count(PromptLog.id)).scalar()

def get_prompt_count_by_user(db: Session, user_id: int) -> int:
    """
    Count prompt logs for a specific user.
    """
    return db.query(func.count(PromptLog.id)).filter(PromptLog.user_id == user_id).scalar()

def get_prompts_within_days(db: Session, days: int = 7, limit: int = 100):
    """
    Get prompts created within the last N days.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(PromptLog)
        .filter(PromptLog.created_at >= cutoff)
        .order_by(PromptLog.created_at.desc())
        .limit(limit)
        .all()
    )

def delete_prompt_by_id(db: Session, prompt_id: int):
    """
    Delete a prompt by ID. Returns True if deleted.
    """
    prompt = db.query(PromptLog).filter(PromptLog.id == prompt_id).first()
    if prompt:
        db.delete(prompt)
        db.commit()
        return True
    return False

# === User Queries ===

def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def get_user_by_api_key(db: Session, api_key: str):
    return db.query(User).filter(User.api_key == api_key).first()

def create_user(db: Session, username: str, api_key: str):
    user = User(username=username, api_key=api_key)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def deactivate_user(db: Session, user_id: int):
    """
    Soft-delete user account by marking as inactive.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.is_active = False
        user.is_deleted = True
        db.commit()
        return True
    return False
