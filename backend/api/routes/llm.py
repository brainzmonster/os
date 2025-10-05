from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from backend.core.engine import engine
import torch
import uuid
import time
from typing import Optional, Dict, Any
from datetime import datetime

# Optional imports (only used if available)
try:
    # Enables token-by-token streaming
    from transformers import TextIteratorStreamer
    HAS_STREAMER = True
except Exception:
    HAS_STREAMER = False

try:
    # Persist prompts to memory if brainz memory service is present
    from backend.services.memory_service import log_prompt
    HAS_MEMORY = True
except Exception:
    HAS_MEMORY = False

router = APIRouter()


# -----------------------------------------------------------------------------
# Request model for standard **non-streaming** generation
# -----------------------------------------------------------------------------
class QueryPayload(BaseModel):
    input: str = Field(..., description="User input prompt")
    max_tokens: int = Field(100, ge=1, le=1024, description="Maximum tokens to generate")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt for injection")

    # NEW: Advanced sampling & control knobs (all optional)
    top_p: Optional[float] = Field(None, ge=0.0, le=1.0, description="Nucleus sampling")
    top_k: Optional[int] = Field(None, ge=0, description="Top-K sampling (0 = disabled)")
    repetition_penalty: Optional[float] = Field(None, ge=0.0, description="Penalty for repeated tokens")
    seed: Optional[int] = Field(None, description="Seed for deterministic sampling (if set)")
    echo_prompt: bool = Field(False, description="If true, return the input prompt alongside the response")
    log_to_memory: bool = Field(False, description="If true, persist the prompt to memory service")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Arbitrary metadata to attach in response")


# -----------------------------------------------------------------------------
# Helper: Compose generation kwargs from payload safely
# -----------------------------------------------------------------------------
def _make_generate_kwargs(payload: QueryPayload) -> Dict[str, Any]:
    """
    Build a kwargs dict for model.generate() from the incoming payload.
    Fields that are None are simply omitted. Keeps the default behavior intact.
    """
    kwargs: Dict[str, Any] = {
        "max_new_tokens": payload.max_tokens,
        "temperature": payload.temperature,
        "do_sample": True,  # Keep sampling behavior as in the original code
    }
    if payload.top_p is not None:
        kwargs["top_p"] = payload.top_p
    if payload.top_k is not None:
        kwargs["top_k"] = payload.top_k
    if payload.repetition_penalty is not None:
        kwargs["repetition_penalty"] = payload.repetition_penalty
    return kwargs


# -----------------------------------------------------------------------------
# POST /api/llm/query — Standard (non-streaming) generation
# -----------------------------------------------------------------------------
@router.post("/api/llm/query")
async def query_llm(payload: QueryPayload, request: Request):
    """
    Synchronous generation endpoint that returns the full decoded text.
    Backwards-compatible with the original behavior, but supports:
    - top_p, top_k, repetition_penalty
    - seed for deterministic runs
    - echo_prompt & metadata passthrough
    - optional log_to_memory
    """
    session_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        llm = engine.get_model()
        model = llm["model"]
        tokenizer = llm["tokenizer"]
        model_name = model.name_or_path if hasattr(model, "name_or_path") else "unknown"

        # Combine system prompt if provided (keeps original semantics)
        full_prompt = f"{payload.system_prompt}\n{payload.input}" if payload.system_prompt else payload.input

        # Optional: seed for reproducibility
        if payload.seed is not None:
            torch.manual_seed(payload.seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(payload.seed)

        # Optional: guardrail against excessive prompt length vs model_max_length
        if hasattr(tokenizer, "model_max_length"):
            # + payload.max_tokens must not drastically exceed the max window; we do a soft check
            encoded_len = len(tokenizer.encode(full_prompt))
            if encoded_len + payload.max_tokens > tokenizer.model_max_length * 2:
                # Soft-limit warning (still allow request)
                # If you prefer hard failure, raise HTTPException(400, ...)
                pass

        # Tokenize input
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
        input_token_count = inputs.input_ids.shape[-1]

        # Build generation kwargs from payload (keeps legacy defaults)
        generate_kwargs = _make_generate_kwargs(payload)

        # Generate output
        with torch.no_grad():
            outputs = model.generate(**inputs, **generate_kwargs)

        # Decode result
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        output_token_count = outputs[0].shape[-1] - input_token_count
        duration = round(time.time() - start_time, 3)

        # Optionally log prompt to memory for recall (best-effort)
        if payload.log_to_memory and HAS_MEMORY:
            try:
                log_prompt(prompt=full_prompt, source="api", tag="inference")
            except Exception:
                # Do not fail the request if memory logging is not available
                pass

        response_data = {
            "session_id": session_id,
            "response": generated,
            "meta": {
                "input_tokens": input_token_count,
                "output_tokens": output_token_count,
                "total_tokens": input_token_count + output_token_count,
                "inference_time": duration,
                "timestamp": datetime.utcnow().isoformat(),
                "model": model_name,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
                "seed": payload.seed,
            },
        }

        if payload.echo_prompt:
            response_data["prompt"] = full_prompt
        if payload.metadata:
            response_data["metadata"] = payload.metadata

        return response_data

    except Exception as e:
        return {
            "session_id": session_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }


# -----------------------------------------------------------------------------
# NEW: Streaming payload model (inherits fields from QueryPayload)
# -----------------------------------------------------------------------------
class StreamQueryPayload(QueryPayload):
    """
    Extends QueryPayload for streaming endpoint. Identical fields,
    kept separate for future stream-specific options (e.g., chunk_size).
    """
    pass


# -----------------------------------------------------------------------------
# NEW ENDPOINT — POST /api/llm/query/stream
# Streams token chunks as Server-Sent Events (SSE-like plain text chunks)
# -----------------------------------------------------------------------------
@router.post("/api/llm/query/stream")
async def query_llm_stream(payload: StreamQueryPayload, request: Request):
    """
    Streaming generation endpoint using transformers.TextIteratorStreamer if available.
    Falls back with 501 if streaming support is not installed.
    """
    if not HAS_STREAMER:
        raise HTTPException(
            status_code=501,
            detail="Streaming not available: install `transformers>=4.28` with TextIteratorStreamer.",
        )

    llm = engine.get_model()
    model = llm["model"]
    tokenizer = llm["tokenizer"]

    # Optional: seed for reproducibility
    if payload.seed is not None:
        torch.manual_seed(payload.seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(payload.seed)

    full_prompt = f"{payload.system_prompt}\n{payload.input}" if payload.system_prompt else payload.input
    inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)

    # Prepare streamer
    streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True)

    # Generate kwargs (reuse helper)
    generate_kwargs = _make_generate_kwargs(payload)
    generate_kwargs.update(
        dict(
            inputs=inputs["input_ids"],
            attention_mask=inputs.get("attention_mask", None),
            streamer=streamer,
        )
    )

    # Background generation function
    def _gen():
        """
        Runs model.generate in a background thread and yields text chunks
        as they become available from the transformer streamer.
        """
        import threading

        def _worker():
            with torch.no_grad():
                model.generate(**generate_kwargs)

        t = threading.Thread(target=_worker)
        t.start()

        for new_text in streamer:
            # Yield chunks as they arrive (plain text lines)
            yield new_text

        t.join()

    # Optional: log the prompt to memory (best-effort)
    if payload.log_to_memory and HAS_MEMORY:
        try:
            log_prompt(prompt=full_prompt, source="api", tag="inference_stream")
        except Exception:
            pass

    # Return a streaming response (text/plain). Consumers can read until EOF.
    headers = {
        "X-Session-ID": str(uuid.uuid4()),
        "X-Timestamp": datetime.utcnow().isoformat(),
    }
    return StreamingResponse(_gen(), media_type="text/plain", headers=headers)
