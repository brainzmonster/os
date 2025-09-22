from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from backend.db.connection import get_db
from backend.db.models import PromptLog
from backend.data.cleaner import full_clean
from backend.utils.tokenizer import count_tokens  # Optional

import logging

logger = logging.getLogger("brainz.memory")


# -----------------------------------------------------------------------------
# Log a new prompt with optional metadata
# -----------------------------------------------------------------------------
def log_prompt(
    prompt: str,
    user_id: int = None,
    tag: str = None,
    source: str = "api",
    allow_duplicates: bool = True
):
    """
    Persist a prompt into the PromptLog table with optional metadata.
    Optionally deduplicates identical prompts over a short lookback window
    to reduce spammy rows.

    Args:
        prompt: Raw user text to persist (will be cleaned).
        user_id: Optional FK to the user that submitted the prompt.
        tag: Optional free-form tag (e.g., "code", "feedback", "general").
        source: Origin of the prompt (e.g., "api", "cli", "ui", "agent").
        allow_duplicates: If False, skip if an identical prompt was logged
                          within the last 60 seconds.
    """
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
        user_id=user_id if hasattr(PromptLog, "user_id") else None,
        tag=tag if hasattr(PromptLog, "tag") else None,
        source=source if hasattr(PromptLog, "source") else None,
        tokens_used=count_tokens(cleaned) if "count_tokens" in globals() and hasattr(PromptLog, "tokens_used") else None,
    )

    db.add(entry)
    db.commit()
    logger.info(f"[brainzaOS] Logged prompt (user={user_id}, tag={tag})")


# -----------------------------------------------------------------------------
# Retrieve recent prompts with optional filters
# -----------------------------------------------------------------------------
def get_recent_prompts(
    limit: int = 10,
    user_id: int = None,
    tag: str = None,
    since_minutes: int = None
):
    """
    Fetch recent prompts, newest first, with optional filters.

    Args:
        limit: Maximum number of rows to return.
        user_id: Only include prompts by this user (if the column exists).
        tag: Filter by tag (if the column exists).
        since_minutes: Only include prompts created within the last N minutes.

    Returns:
        List[PromptLog]: ORM rows.
    """
    db: Session = next(get_db())

    query = db.query(PromptLog).order_by(PromptLog.created_at.desc())

    if user_id and hasattr(PromptLog, "user_id"):
        query = query.filter(PromptLog.user_id == user_id)
    if tag and hasattr(PromptLog, "tag"):
        query = query.filter(PromptLog.tag == tag)
    if since_minutes:
        cutoff = datetime.utcnow() - timedelta(minutes=since_minutes)
        query = query.filter(PromptLog.created_at >= cutoff)

    return query.limit(limit).all()


# -----------------------------------------------------------------------------
# NEW: Lightweight memory analytics / health snapshot
# -----------------------------------------------------------------------------
def get_memory_stats(
    since_days: int | None = None,
    user_id: int | None = None,
    tag: str | None = None,
) -> dict:
    """
    Return a compact analytics snapshot of the prompt memory table.
    This is useful for dashboards, CLI health checks, and agent heuristics.

    Metrics included:
      - total: total prompt rows in scope
      - first_ts / last_ts: oldest/newest timestamps in scope (ISO)
      - avg_tokens: average tokens_used (if column and count function are available)
      - by_tag: frequency map of tags (if 'tag' column exists)
      - by_source: frequency map of sources (if 'source' column exists)
      - by_user: top-10 users by row count (if 'user_id' column exists)

    Args:
        since_days: If provided, only include rows since now - N days.
        user_id: Optional filter to a single user (if the column exists).
        tag: Optional filter to a specific tag (if the column exists).

    Returns:
        dict: Aggregated stats.
    """
    db: Session = next(get_db())

    # Base query with optional time and attribute filters
    q = db.query(PromptLog)
    if since_days:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
        q = q.filter(PromptLog.created_at >= cutoff)
    if user_id and hasattr(PromptLog, "user_id"):
        q = q.filter(PromptLog.user_id == user_id)
    if tag and hasattr(PromptLog, "tag"):
        q = q.filter(PromptLog.tag == tag)

    # Total rows in scope
    total = q.count()

    # Oldest / newest timestamps (empty-safe)
    first_row = q.order_by(PromptLog.created_at.asc()).first()
    last_row = q.order_by(PromptLog.created_at.desc()).first()
    first_ts = first_row.created_at.isoformat() if first_row else None
    last_ts = last_row.created_at.isoformat() if last_row else None

    # Average tokens if schema supports it
    avg_tokens = None
    if hasattr(PromptLog, "tokens_used"):
        avg_tokens = db.query(func.avg(PromptLog.tokens_used)).filter(PromptLog.id.in_([row.id for row in q.all()])).scalar()
        if avg_tokens is not None:
            avg_tokens = round(float(avg_tokens), 2)

    # Group-by helpers (defensive: only compute if columns exist)
    by_tag = {}
    if hasattr(PromptLog, "tag"):
        g = (
            db.query(PromptLog.tag, func.count(PromptLog.id))
            .filter(PromptLog.id.in_([row.id for row in q.all()]))
            .group_by(PromptLog.tag)
            .all()
        )
        by_tag = {k or "untagged": v for k, v in g}

    by_source = {}
    if hasattr(PromptLog, "source"):
        g = (
            db.query(PromptLog.source, func.count(PromptLog.id))
            .filter(PromptLog.id.in_([row.id for row in q.all()]))
            .group_by(PromptLog.source)
            .all()
        )
        by_source = {k or "unknown": v for k, v in g}

    by_user = {}
    if hasattr(PromptLog, "user_id"):
        g = (
            db.query(PromptLog.user_id, func.count(PromptLog.id))
            .filter(PromptLog.id.in_([row.id for row in q.all()]))
            .group_by(PromptLog.user_id)
            .order_by(func.count(PromptLog.id).desc())
            .limit(10)
            .all()
        )
        by_user = {str(k) if k is not None else "anonymous": v for k, v in g}

    snapshot = {
        "total": total,
        "first_ts": first_ts,
        "last_ts": last_ts,
        "avg_tokens": avg_tokens,
        "by_tag": by_tag,
        "by_source": by_source,
        "by_user": by_user,
        "window_days": since_days,
        "filters": {
            "user_id": user_id,
            "tag": tag,
        },
    }

    logger.info(
        "[brainzaOS] Memory stats — total=%s, window_days=%s, tag=%s, user=%s",
        total, since_days, tag, user_id
    )
    return snapshot
