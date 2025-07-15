from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.db.connection import get_db
from backend.db.models import PromptLog
from backend.data.cleaner import full_clean
from backend.utils.tokenizer import count_tokens  # Optional

import logging

logger = logging.getLogger("brainz.memory")


# Log a new prompt with optional metadata
def log_prompt(
    prompt: str,
    user_id: int = None,
    tag: str = None,
    source: str = "api",
    allow_duplicates: bool = True
):
    db: Session = next(get_db())
    cleaned = full_clean(prompt)

    # Optional deduplication logic (same prompt in recent 60s)
    if not allow_duplicates:
        recent = (
            db.query(PromptLog)
            .filter(PromptLog.prompt == cleaned)
            .order_by(PromptLog.created_at.desc())
            .first()
        )
        if recent and (datetime.utcnow() - recent.created_at).seconds < 60:
            logger.info("[brainzaOS] Skipping duplicate prompt.")
            return

    entry = PromptLog(
        prompt=cleaned,
        user_id=user_id,
        tag=tag,
        source=source,
        tokens_used=count_tokens(cleaned) if "count_tokens" in globals() else None,
    )

    db.add(entry)
    db.commit()
    logger.info(f"[brainzaOS] Logged prompt (user={user_id}, tag={tag})")


# Retrieve recent prompts with optional filters
def get_recent_prompts(
    limit: int = 10,
    user_id: int = None,
    tag: str = None,
    since_minutes: int = None
):
    db: Session = next(get_db())

    query = db.query(PromptLog).order_by(PromptLog.created_at.desc())

    if user_id:
        query = query.filter(PromptLog.user_id == user_id)
    if tag:
        query = query.filter(PromptLog.tag == tag)
    if since_minutes:
        cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
        query = query.filter(PromptLog.created_at >= cutoff)

    return query.limit(limit).all()
