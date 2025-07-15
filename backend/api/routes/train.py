from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field
from backend.models.trainer import fine_tune_model
from backend.core.engine import engine
from datetime import datetime
from typing import List, Optional
import uuid
import logging

router = APIRouter()
logger = logging.getLogger("LLMTrainer")
logging.basicConfig(level=logging.INFO)

# Request payload for fine-tuning
class TrainPayload(BaseModel):
    texts: List[str] = Field(..., min_items=1, description="List of training prompts/completions")
    dry_run: Optional[bool] = Field(False, description="If True, simulates training without executing")
    tags: Optional[List[str]] = Field(default_factory=list, description="Optional tags for tracking")
    source: Optional[str] = Field("api", description="Where the training request originated from")


@router.post("/api/llm/train")
async def train_llm(payload: TrainPayload, request: Request):
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")

    if not payload.texts or not isinstance(payload.texts, list):
        raise HTTPException(status_code=400, detail="Invalid training data. Must be a non-empty list.")

    try:
        # Estimate token count using active tokenizer
        tokenizer = engine.get_model()["tokenizer"]
        total_tokens = sum(len(tokenizer.encode(txt)) for txt in payload.texts)

        logger.info(f"[{session_id}] Received training request — {len(payload.texts)} entries, {total_tokens} tokens.")

        if payload.dry_run:
            logger.info(f"[{session_id}] Dry-run mode: Skipping actual training.")
        else:
            fine_tune_model(payload.texts)
            logger.info(f"[{session_id}] Model fine-tuning executed successfully.")

        return {
            "status": "success" if not payload.dry_run else "simulated",
            "trained_samples": len(payload.texts),
            "estimated_tokens": total_tokens,
            "dry_run": payload.dry_run,
            "tags": payload.tags,
            "source": payload.source,
            "meta": {
                "session_id": session_id,
                "timestamp": timestamp,
                "client_ip": client_ip,
                "user_agent": user_agent
            }
        }

    except Exception as e:
        logger.error(f"[{session_id}] Training failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Model training failed.",
                "reason": str(e),
                "session_id": session_id,
                "timestamp": timestamp
            }
        )
 