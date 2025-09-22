from backend.models.trainer import fine_tune_model
from backend.services.memory_service import get_recent_prompts
from backend.utils.tokenizer import count_tokens  # Optional
from datetime import datetime

import logging

logger = logging.getLogger("brainz.training")


# -----------------------------------------------------------------------------
# Central training control — triggered manually, by schedule, or by an agent
# -----------------------------------------------------------------------------
def run_recent_prompt_training(
    limit: int = 20,
    min_length: int = 5,
    tag: str = None,
    user_id: int = None,
    deduplicate: bool = True,
    min_tokens: int = 5,
    since_minutes: int = None
):
    """
    Retrieve recent prompts from memory and trigger model fine-tuning.

    Args:
        limit (int): Max number of recent prompts
        min_length (int): Minimum length of prompt string
        tag (str): Optional filter by prompt tag
        user_id (int): Optional user filter
        deduplicate (bool): Remove duplicate prompts
        min_tokens (int): Minimum token count
        since_minutes (int): Restrict to recent prompt timeframe

    Returns:
        dict: Summary of training trigger event
    """
    prompts = get_recent_prompts(
        limit=limit * 2,  # Fetch more for filtering headroom
        tag=tag,
        user_id=user_id,
        since_minutes=since_minutes,
    )

    # Filtering pipeline (length, dedupe, token threshold)
    texts = []
    seen = set()

    for p in prompts:
        if not p.prompt or len(p.prompt.strip()) < min_length:
            continue
        if deduplicate and p.prompt in seen:
            continue
        if count_tokens and count_tokens(p.prompt) < min_tokens:
            continue
        texts.append(p.prompt)
        seen.add(p.prompt)
        if len(texts) >= limit:
            break

    if not texts:
        logger.info("[brainzaOS] No valid prompts found for training.")
        return {"trained": False, "samples": 0, "reason": "no_valid_prompts"}

    logger.info(f"[brainzaOS] Training on {len(texts)} recent prompts")
    fine_tune_model(texts)

    return {
        "trained": True,
        "samples": len(texts),
        "tag": tag,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }


# -----------------------------------------------------------------------------
# NEW: Dry-run/preview utility — see what would be trained without training
# -----------------------------------------------------------------------------
def preview_recent_prompt_training(
    limit: int = 20,
    min_length: int = 5,
    tag: str = None,
    user_id: int = None,
    deduplicate: bool = True,
    min_tokens: int = 5,
    since_minutes: int = None,
    include_snippets: bool = True,
    snippet_len: int = 120,
):
    """
    Preview the set of prompts that *would* be used for training given the same
    filtering parameters as `run_recent_prompt_training`, but WITHOUT invoking
    `fine_tune_model`. Useful for dashboards/CLIs/agents to validate a batch
    before committing compute.

    Args:
        limit (int): Max number of prompts to return after filtering.
        min_length (int): Minimum character length for inclusion.
        tag (str): Optional tag filter (requires column support).
        user_id (int): Optional user filter (requires column support).
        deduplicate (bool): If True, drop duplicates in the selection window.
        min_tokens (int): Minimum token count threshold (if tokenizer available).
        since_minutes (int): Only consider prompts in a recent time window.
        include_snippets (bool): Include shortened text previews for UI.
        snippet_len (int): Max preview length per snippet.

    Returns:
        dict: {
            "candidates": [<prompt strings>],
            "count": int,
            "total_seen": int,
            "avg_tokens": float | None,
            "min_tokens": int | None,
            "max_tokens": int | None,
            "snippets": [<truncated previews>]  # if include_snippets
            "filters": {...},
            "timestamp": iso8601
        }
    """
    prompts = get_recent_prompts(
        limit=limit * 2,  # over-fetch to allow pruning
        tag=tag,
        user_id=user_id,
        since_minutes=since_minutes,
    )

    total_seen = len(prompts)
    candidates = []
    seen = set()
    token_list = []

    for p in prompts:
        text = (p.prompt or "").strip()
        if len(text) < min_length:
            continue
        if deduplicate and text in seen:
            continue

        # Token threshold if tokenizer is available; otherwise accept
        tok_count = None
        if count_tokens:
            try:
                tok_count = count_tokens(text)
            except Exception:
                tok_count = None

        if tok_count is not None and tok_count < min_tokens:
            continue

        candidates.append(text)
        seen.add(text)
        if tok_count is not None:
            token_list.append(tok_count)

        if len(candidates) >= limit:
            break

    # Compute token stats (if we collected any)
    avg_tokens = round(sum(token_list) / len(token_list), 2) if token_list else None
    min_tok = min(token_list) if token_list else None
    max_tok = max(token_list) if token_list else None

    payload = {
        "candidates": candidates,
        "count": len(candidates),
        "total_seen": total_seen,
        "avg_tokens": avg_tokens,
        "min_tokens": min_tok,
        "max_tokens": max_tok,
        "filters": {
            "limit": limit,
            "min_length": min_length,
            "tag": tag,
            "user_id": user_id,
            "deduplicate": deduplicate,
            "min_tokens": min_tokens,
            "since_minutes": since_minutes,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }

    if include_snippets:
        payload["snippets"] = [
            (c[:snippet_len] + "…") if len(c) > snippet_len else c
            for c in candidates
        ]

    logger.info(
        "[brainzaOS] Preview training — %s/%s candidates (avg_tokens=%s)",
        len(candidates), total_seen, avg_tokens
    )
    return payload
