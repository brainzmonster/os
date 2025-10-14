from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from backend.db.models import PromptLog, User

# =============================================================================
# Prompt Queries
# =============================================================================

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


# -----------------------------------------------------------------------------
# NEW: Prompt analytics helpers (non-breaking additions)
# -----------------------------------------------------------------------------

def get_top_tags(db: Session, limit: int = 10) -> List[Dict[str, int]]:
    """
    Return the most frequent prompt tags and their counts.
    Useful for quick analytics / dashboards.
    """
    rows = (
        db.query(PromptLog.tag, func.count(PromptLog.id).label("count"))
        .filter(PromptLog.tag.isnot(None))
        .group_by(PromptLog.tag)
        .order_by(desc("count"))
        .limit(limit)
        .all()
    )
    return [{"tag": r[0], "count": r[1]} for r in rows]


def get_prompts_summary_by_day(
    db: Session,
    days: int = 7,
    user_id: Optional[int] = None,
    tag: Optional[str] = None,
) -> List[Dict[str, int]]:
    """
    Aggregate prompt counts per UTC day over the given window.
    Returns a list of dicts: [{date: 'YYYY-MM-DD', count: N}, ...]
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    query = db.query(
        func.date_trunc("day", PromptLog.created_at).label("day"),
        func.count(PromptLog.id).label("count"),
    ).filter(PromptLog.created_at >= cutoff)

    if user_id is not None:
        query = query.filter(PromptLog.user_id == user_id)
    if tag is not None:
        query = query.filter(PromptLog.tag == tag)

    rows = (
        query.group_by(func.date_trunc("day", PromptLog.created_at))
        .order_by(func.date_trunc("day", PromptLog.created_at))
        .all()
    )

    return [{"date": row[0].date().isoformat(), "count": row[1]} for row in rows]


def get_recent_unique_prompts(
    db: Session,
    limit: int = 50,
    min_length: int = 5,
) -> List[PromptLog]:
    """
    Retrieve recent prompts ensuring uniqueness by exact prompt text.
    Keeps the most recent entry for duplicate texts.
    """
    # First, order recent prompts; then deduplicate in Python to keep portability.
    rows = (
        db.query(PromptLog)
        .order_by(PromptLog.created_at.desc())
        .limit(limit * 5)  # fetch extra to allow deduplication
        .all()
    )

    seen = set()
    unique: List[PromptLog] = []
    for row in rows:
        text = (row.prompt or "").strip()
        if len(text) < min_length:
            continue
        if text in seen:
            continue
        seen.add(text)
        unique.append(row)
        if len(unique) >= limit:
            break
    return unique


def bulk_delete_prompts_by_tag(
    db: Session,
    tag: str,
    older_than_days: Optional[int] = None,
) -> int:
    """
    Danger-zone utility: bulk delete prompts by tag with an optional age guard.
    Returns the number of deleted rows.
    """
    query = db.query(PromptLog).filter(PromptLog.tag == tag)
    if older_than_days is not None:
        cutoff = datetime.utcnow() - timedelta(days=older_than_days)
        query = query.filter(PromptLog.created_at < cutoff)

    # Count first (so we can report), then delete
    to_delete = query.count()
    if to_delete > 0:
        query.delete(synchronize_session=False)
        db.commit()
    return to_delete


# =============================================================================
# User Queries
# =============================================================================

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


# -----------------------------------------------------------------------------
# NEW: User analytics & helpers (non-breaking additions)
# -----------------------------------------------------------------------------

def get_top_users_by_prompts(
    db: Session,
    limit: int = 10,
    active_only: bool = True,
) -> List[Dict[str, int]]:
    """
    Rank users by number of associated PromptLogs.
    """
    query = (
        db.query(User.username, func.count(PromptLog.id).label("count"))
        .join(PromptLog, PromptLog.user_id == User.id, isouter=True)
        .group_by(User.id, User.username)
        .order_by(desc("count"))
        .limit(limit)
    )
    if active_only:
        query = query.filter(User.is_active.is_(True))
    rows = query.all()
    return [{"username": r[0], "count": r[1]} for r in rows]


def touch_user_access(db: Session, user_id: int) -> bool:
    """
    Update last_accessed and bump usage_count for the user.
    Mirrors the convenience method on the model; kept here for a pure-query path.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    # Keep logic simple and DB-side safe
    user.usage_count = (user.usage_count or 0) + 1
    user.last_accessed = datetime.utcnow()
    db.commit()
    return True


def get_active_users(db: Session, limit: int = 100) -> List[User]:
    """
    Return a list of currently active users.
    """
    return db.query(User).filter(User.is_active.is_(True)).limit(limit).all()
