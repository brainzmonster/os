from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from backend.db.connection import get_db
from backend.db.models import PromptLog
from backend.utils.tokenizer import count_tokens  # Optional if available

import logging

logger = logging.getLogger("brainz.analytics")

def get_most_common_prompts(
    limit: int = 20,
    min_length: int = 5,
    since_days: int = None,
    tag: str = None,
    user_id: int = None,
    case_insensitive: bool = False,
    return_raw: bool = False
):
    """
    Fetch the most frequently submitted prompts from the database.

    Args:
        limit (int): Max number of results
        min_length (int): Minimum character length of prompt
        since_days (int): Filter to last N days
        tag (str): Filter by tag (e.g. "code", "feedback")
        user_id (int): Only fetch prompts from this user
        case_insensitive (bool): Group case-insensitively
        return_raw (bool): Return raw SQLAlchemy rows

    Returns:
        list[dict] or list[Row]: Prompt text with count
    """

    db: Session = next(get_db())

    query = db.query(
        PromptLog.prompt if not case_insensitive else func.lower(PromptLog.prompt),
        func.count(PromptLog.prompt).label("count")
    )

    # Optional filters
    if tag:
        query = query.filter(PromptLog.tag == tag)
    if user_id:
        query = query.filter(PromptLog.user_id == user_id)
    if since_days:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
        query = query.filter(PromptLog.created_at >= cutoff)

    if case_insensitive:
        query = query.group_by(func.lower(PromptLog.prompt))
    else:
        query = query.group_by(PromptLog.prompt)

    query = query.order_by(func.count(PromptLog.prompt).desc()).limit(limit)

    results = query.all()

    filtered = []
    for r in results:
        prompt_text = r[0]
        if len(prompt_text.strip()) >= min_length:
            filtered.append({
                "prompt": prompt_text,
                "count": r[1],
                "tokens": count_tokens(prompt_text) if "count_tokens" in globals() else None
            })

    if return_raw:
        return results
    return filtered
