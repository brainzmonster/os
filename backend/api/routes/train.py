from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import uuid
import logging
import statistics

from backend.models.trainer import fine_tune_model
from backend.core.engine import engine

# Optional text cleanup (keeps backward-compat if not present)
try:
    from backend.data.cleaner import full_clean
except Exception:  # pragma: no cover
    full_clean = lambda x: x  # no-op fallback

router = APIRouter()
logger = logging.getLogger("LLMTrainer")
logging.basicConfig(level=logging.INFO)


# -----------------------------------------------------------------------------
# Request payload for fine-tuning
# -----------------------------------------------------------------------------
class TrainPayload(BaseModel):
    texts: List[str] = Field(..., min_items=1, description="List of training prompts/completions")
    dry_run: Optional[bool] = Field(False, description="If True, simulates training without executing")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional tags for tracking")
    source: Optional[str] = Field("api", description="Where the training request originated from")

    # NEW (optional knobs, default off => preserves existing behavior)
    clean: Optional[bool] = Field(False, description="Apply basic text cleaning before training")
    deduplicate: Optional[bool] = Field(True, description="Drop exact duplicates before training")
    min_length: Optional[int] = Field(0, ge=0, description="Filter out items with fewer than N characters")


# -----------------------------------------------------------------------------
# Internal helpers (kept small & stateless)
# -----------------------------------------------------------------------------
def _get_tokenizer_safe():
    """
    Retrieve the active tokenizer from the engine.
    Returns None if unavailable to keep endpoints resilient.
    """
    try:
        return engine.get_model()["tokenizer"]
    except Exception:
        return None


def _estimate_tokens(texts: List[str]) -> int:
    """
    Estimate the token usage for a list of texts using the active tokenizer.
    Returns -1 if a tokenizer is not available (e.g., engine not booted yet).
    """
    tok = _get_tokenizer_safe()
    if tok is None:
        return -1
    return sum(len(tok.encode(txt)) for txt in texts)


def _prepare_texts(
    texts: List[str], *, clean: bool, deduplicate: bool, min_length: int
) -> Tuple[List[str], Dict[str, Any]]:
    """
    Apply optional cleaning, deduplication and length filtering.
    Returns the processed list and a small stats dict about what changed.
    """
    original_count = len(texts)

    # Clean
    if clean:
        texts = [full_clean(t) for t in texts]

    # Min-length filter (character-based to avoid tokenizer dependency)
    if min_length and min_length > 0:
        texts = [t for t in texts if len(t) >= min_length]

    # Deduplicate (exact match)
    if deduplicate:
        seen = set()
        deduped = []
        for t in texts:
            if t not in seen:
                deduped.append(t)
                seen.add(t)
        texts = deduped

    processed_count = len(texts)
    return texts, {
        "original": original_count,
        "processed": processed_count,
        "removed": original_count - processed_count,
        "clean_applied": clean,
        "deduplicated": deduplicate,
        "min_length": min_length,
    }


# -----------------------------------------------------------------------------
# POST /api/llm/train — fine-tune the model
# -----------------------------------------------------------------------------
@router.post("/api/llm/train")
async def train_llm(payload: TrainPayload, request: Request):
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")

    if not payload.texts or not isinstance(payload.texts, list):
        raise HTTPException(status_code=400, detail="Invalid training data. Must be a non-empty list.")

    # Prepare the data (optional cleaning/dedup/length filtering)
    processed_texts, prep_stats = _prepare_texts(
        payload.texts,
        clean=bool(payload.clean),
        deduplicate=bool(payload.deduplicate),
        min_length=int(payload.min_length or 0),
    )

    if not processed_texts:
        raise HTTPException(status_code=422, detail="All samples were filtered out (empty after preprocessing).")

    try:
        # Estimate token count using active tokenizer (safe if engine not ready)
        total_tokens = _estimate_tokens(processed_texts)

        logger.info(
            f"[{session_id}] Training request — "
            f"{prep_stats['processed']}/{prep_stats['original']} samples after preprocessing, "
            f"tokens={total_tokens if total_tokens >= 0 else 'unknown'}"
        )

        if payload.dry_run:
            logger.info(f"[{session_id}] Dry-run mode: Skipping actual training.")
        else:
            # Execute the fine-tuning with the processed list (backward-compatible call)
            fine_tune_model(processed_texts)
            logger.info(f"[{session_id}] Model fine-tuning executed successfully.")

        return {
            "status": "success" if not payload.dry_run else "simulated",
            "trained_samples": len(processed_texts),
            "estimated_tokens": total_tokens,
            "dry_run": payload.dry_run,
            "tags": payload.tags,
            "source": payload.source,
            "preprocess": prep_stats,
            "meta": {
                "session_id": session_id,
                "timestamp": timestamp,
                "client_ip": client_ip,
                "user_agent": user_agent,
            },
        }

    except Exception as e:
        logger.error(f"[{session_id}] Training failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Model training failed.",
                "reason": str(e),
                "session_id": session_id,
                "timestamp": timestamp,
            },
        )


# -----------------------------------------------------------------------------
# NEW: POST /api/llm/train/estimate — preview token + quality stats without training
# -----------------------------------------------------------------------------
class EstimatePayload(BaseModel):
    texts: List[str] = Field(..., min_items=1, description="Samples to analyze (no training performed)")
    clean: Optional[bool] = Field(False, description="Apply the same cleaning as the trainer")
    deduplicate: Optional[bool] = Field(True, description="Drop exact duplicates before computing stats")
    min_length: Optional[int] = Field(0, ge=0, description="Filter out items with fewer than N characters")


@router.post("/api/llm/train/estimate")
async def estimate_training(payload: EstimatePayload, request: Request):
    """
    Returns token estimates and quick quality stats for a set of samples.
    This mirrors the trainer's preprocessing so you can preview the effect.
    """
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()

    if not payload.texts or not isinstance(payload.texts, list):
        raise HTTPException(status_code=400, detail="Invalid input. Provide a non-empty 'texts' list.")

    # Apply the same preprocessing path as /api/llm/train
    processed_texts, prep_stats = _prepare_texts(
        payload.texts,
        clean=bool(payload.clean),
        deduplicate=bool(payload.deduplicate),
        min_length=int(payload.min_length or 0),
    )

    if not processed_texts:
        return {
            "status": "empty",
            "message": "All samples were filtered out by preprocessing.",
            "preprocess": prep_stats,
            "meta": {"session_id": session_id, "timestamp": timestamp},
        }

    # Compute token estimate & basic stats (lengths in chars for tokenizer-agnostic view)
    tok_total = _estimate_tokens(processed_texts)
    lengths = [len(t) for t in processed_texts]

    stats = {
        "count": len(processed_texts),
        "chars_min": min(lengths),
        "chars_max": max(lengths),
        "chars_avg": round(statistics.mean(lengths), 2),
        "chars_median": statistics.median(lengths),
        "token_estimate_total": tok_total,
        "token_estimate_avg": None if tok_total < 0 else round(tok_total / len(processed_texts), 2),
    }

    return {
        "status": "ok",
        "preview_only": True,
        "preprocess": prep_stats,
        "stats": stats,
        "meta": {
            "session_id": session_id,
            "timestamp": timestamp,
            "client_ip": request.client.host,
            "user_agent": request.headers.get("user-agent"),
        },
    }
