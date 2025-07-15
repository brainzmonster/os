from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from backend.core.engine import engine
import torch
import uuid
import time
from typing import Optional
from datetime import datetime

router = APIRouter()


class QueryPayload(BaseModel):
    input: str = Field(..., description="User input prompt")
    max_tokens: int = Field(100, ge=1, le=1024, description="Maximum tokens to generate")
    temperature: float = Field(0.7, ge=0.0, le=1.0, description="Sampling temperature")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt for injection")


@router.post("/api/llm/query")
async def query_llm(payload: QueryPayload, request: Request):
    session_id = str(uuid.uuid4())
    start_time = time.time()

    try:
        llm = engine.get_model()
        model = llm["model"]
        tokenizer = llm["tokenizer"]
        model_name = model.name_or_path if hasattr(model, "name_or_path") else "unknown"

        # Combine system prompt if provided
        full_prompt = f"{payload.system_prompt}\n{payload.input}" if payload.system_prompt else payload.input

        # Tokenize input
        inputs = tokenizer(full_prompt, return_tensors="pt").to(model.device)
        input_token_count = inputs.input_ids.shape[-1]

        # Generate output
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=payload.max_tokens,
                temperature=payload.temperature,
                do_sample=True
            )

        # Decode result
        generated = tokenizer.decode(outputs[0], skip_special_tokens=True)
        output_token_count = outputs[0].shape[-1] - input_token_count
        duration = round(time.time() - start_time, 3)

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
                "user_agent": request.headers.get("user-agent")
            }
        }

        # Optional: persist this query to DB or log system
        # log_query(session_id, full_prompt, generated, response_data["meta"])

        return response_data

    except Exception as e:
        return {
            "session_id": session_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }
