from backend.models.trainer import fine_tune_model
from backend.services.memory_service import get_recent_prompts
from backend.utils.tokenizer import count_tokens  # Optional
from datetime import datetime

import logging

logger = logging.getLogger("brainz.training")

# Central training control — triggered manually, by schedule, or agent
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
        limit=limit * 2,  # Fetch more for filtering
        tag=tag,
        user_id=user_id,
        since_minutes=since_minutes,
    )

    # Basic validation
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
