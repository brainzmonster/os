from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Dict, Optional

from backend.db.connection import get_db
from backend.db.models import PromptLog
from backend.utils.tokenizer import count_tokens  # Optional if available

import logging

logger = logging.getLogger("brainz.analytics")


def get_most_common_prompts(
    limit: int = 20,
    min_length: int = 5,
    since_days: Optional[int] = None,
    tag: Optional[str] = None,
    user_id: Optional[int] = None,
    case_insensitive: bool = False,
    return_raw: bool = False
):
    """
    Fetch the most frequently submitted prompts from the database.

    Args:
        limit (int): Max number of results.
        min_length (int): Minimum character length of prompt (post-strip).
        since_days (int|None): Filter to the last N days if provided.
        tag (str|None): Filter by tag (e.g., "code", "feedback") if the column exists.
        user_id (int|None): Only fetch prompts from this user if the column exists.
        case_insensitive (bool): Group case-insensitively.
        return_raw (bool): If True, return raw SQLAlchemy rows instead of dicts.

    Returns:
        list[dict] or list[Row]: Prompt text with count (and optional token count).
    """
    db: Session = next(get_db())

    # Select clause: case-insensitive grouping can use LOWER() on prompt
    select_prompt = PromptLog.prompt if not case_insensitive else func.lower(PromptLog.prompt)

    query = db.query(
        select_prompt,
        func.count(PromptLog.prompt).label("count"),
    )

    # Optional filters (defensively check for columns that may not exist in older schemas)
    if tag and hasattr(PromptLog, "tag"):
        query = query.filter(PromptLog.tag == tag)
    if user_id and hasattr(PromptLog, "user_id"):
        query = query.filter(PromptLog.user_id == user_id)
    if since_days:
        cutoff = datetime.utcnow() - timedelta(days=since_days)
        query = query.filter(PromptLog.created_at >= cutoff)

    # Grouping
    if case_insensitive:
        query = query.group_by(func.lower(PromptLog.prompt))
    else:
        query = query.group_by(PromptLog.prompt)

    # Order + limit
    query = query.order_by(func.count(PromptLog.prompt).desc()).limit(limit)

    results = query.all()

    # Post-filter short entries and attach optional token counts
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


# -----------------------------------------------------------------------------
# NEW: Daily prompt activity trend (time-series) with lightweight stats
# -----------------------------------------------------------------------------
def get_prompt_trend(
    days: int = 7,
    tag: Optional[str] = None,
    user_id: Optional[int] = None,
    case_insensitive: bool = False,
) -> List[Dict[str, Optional[float]]]:
    """
    Build a day-level prompt activity time series with simple analytics.

    This function complements `get_most_common_prompts` by returning
    per-day aggregates for the last `days` days. It is DB-agnostic:
    it will try to use SQL day-bucketing for PostgreSQL (date_trunc),
    but falls back to Python-side aggregation if needed.

    Metrics per day:
        - date: ISO date string (UTC)
        - count: total number of prompt rows that day
        - unique_prompts: number of unique prompt strings that day
        - avg_len: average character length (post-strip)
        - avg_tokens: average token length (if tokenizer/count available, else None)

    Args:
        days (int): Lookback window length in days (inclusive of today).
        tag (str|None): Optional tag filter (if column exists).
        user_id (int|None): Optional user filter (if column exists).
        case_insensitive (bool): If True, uniqueness is computed case-insensitively.

    Returns:
        List[dict]: one entry per date (ascending), each with the metrics above.
    """
    db: Session = next(get_db())

    start = datetime.utcnow() - timedelta(days=days - 1)  # Include today as day #1
    # Try to build a DB-level date bucket using date_trunc if available (Postgres).
    # If DB doesn't support date_trunc, we will fetch rows and aggregate in Python.
    can_date_trunc = True
    try:
        # Quick no-op to assert function exists in dialect (will still catch at execute time)
        _ = func.date_trunc("day", PromptLog.created_at)
    except Exception:
        can_date_trunc = False

    if can_date_trunc:
        try:
            # Build base query with optional filters
            base = db.query(
                func.date_trunc("day", PromptLog.created_at).label("bucket"),
                PromptLog.prompt
            ).filter(PromptLog.created_at >= start)

            if tag and hasattr(PromptLog, "tag"):
                base = base.filter(PromptLog.tag == tag)
            if user_id and hasattr(PromptLog, "user_id"):
                base = base.filter(PromptLog.user_id == user_id)

            rows = base.all()

            # Python-side aggregation of the returned rows
            buckets: Dict[str, Dict[str, any]] = defaultdict(lambda: {
                "date": None,
                "count": 0,
                "unique_set": set(),
                "len_sum": 0,
                "tok_sum": 0,
                "tok_count": 0,
            })

            for bucket_dt, prompt in rows:
                # Normalize date to YYYY-MM-DD
                date_key = bucket_dt.date().isoformat()
                rec = buckets[date_key]
                rec["date"] = date_key
                rec["count"] += 1

                # Uniqueness (case-insensitive optional)
                unique_key = prompt.lower() if case_insensitive and isinstance(prompt, str) else prompt
                rec["unique_set"].add(unique_key)

                # Lengths
                if isinstance(prompt, str):
                    s = prompt.strip()
                    rec["len_sum"] += len(s)

                    if "count_tokens" in globals():
                        try:
                            rec["tok_sum"] += count_tokens(s) or 0
                            rec["tok_count"] += 1
                        except Exception:
                            pass

            # Build contiguous date range and backfill zero-days
            out = []
            for i in range(days):
                day_key = (start + timedelta(days=i)).date().isoformat()
                rec = buckets.get(day_key, None)
                if not rec:
                    out.append({
                        "date": day_key,
                        "count": 0,
                        "unique_prompts": 0,
                        "avg_len": 0.0,
                        "avg_tokens": None if "count_tokens" not in globals() else 0.0,
                    })
                else:
                    avg_len = (rec["len_sum"] / rec["count"]) if rec["count"] > 0 else 0.0
                    avg_tokens = None
                    if "count_tokens" in globals() and rec["tok_count"] > 0:
                        avg_tokens = rec["tok_sum"] / rec["tok_count"]
                    out.append({
                        "date": rec["date"],
                        "count": rec["count"],
                        "unique_prompts": len(rec["unique_set"]),
                        "avg_len": round(avg_len, 2),
                        "avg_tokens": None if avg_tokens is None else round(avg_tokens, 2),
                    })
            return out

        except Exception as e:
            logger.warning(f"[analytics] date_trunc aggregation failed, falling back to Python grouping: {e}")

    # Fallback: fetch rows and aggregate purely in Python (portable across DBs)
    base = db.query(PromptLog.created_at, PromptLog.prompt).filter(PromptLog.created_at >= start)
    if tag and hasattr(PromptLog, "tag"):
        base = base.filter(PromptLog.tag == tag)
    if user_id and hasattr(PromptLog, "user_id"):
        base = base.filter(PromptLog.user_id == user_id)

    rows = base.all()

    buckets: Dict[str, Dict[str, any]] = defaultdict(lambda: {
        "date": None,
        "count": 0,
        "unique_set": set(),
        "len_sum": 0,
        "tok_sum": 0,
        "tok_count": 0,
    })

    for created_at, prompt in rows:
        # Normalize date to UTC ISO date
        day_key = (created_at if isinstance(created_at, datetime) else datetime.utcnow()).date().isoformat()
        rec = buckets[day_key]
        rec["date"] = day_key
        rec["count"] += 1

        unique_key = prompt.lower() if case_insensitive and isinstance(prompt, str) else prompt
        rec["unique_set"].add(unique_key)

        if isinstance(prompt, str):
            s = prompt.strip()
            rec["len_sum"] += len(s)
            if "count_tokens" in globals():
                try:
                    rec["tok_sum"] += count_tokens(s) or 0
                    rec["tok_count"] += 1
                except Exception:
                    pass

    out: List[Dict[str, Optional[float]]] = []
    for i in range(days):
        day_key = (start + timedelta(days=i)).date().isoformat()
        rec = buckets.get(day_key, None)
        if not rec:
            out.append({
                "date": day_key,
                "count": 0,
                "unique_prompts": 0,
                "avg_len": 0.0,
                "avg_tokens": None if "count_tokens" not in globals() else 0.0,
            })
        else:
            avg_len = (rec["len_sum"] / rec["count"]) if rec["count"] > 0 else 0.0
            avg_tokens = None
            if "count_tokens" in globals() and rec["tok_count"] > 0:
                avg_tokens = rec["tok_sum"] / rec["tok_count"]
            out.append({
                "date": rec["date"],
                "count": rec["count"],
                "unique_prompts": len(rec["unique_set"]),
                "avg_len": round(avg_len, 2),
                "avg_tokens": None if avg_tokens is None else round(avg_tokens, 2),
            })

    return out
