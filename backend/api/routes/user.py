from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr, validator
from backend.services.user_service import create_user, get_user_by_name
from datetime import datetime
import uuid
from typing import Optional

router = APIRouter()

# Reserved usernames (can be expanded as needed)
RESERVED_USERNAMES = {"admin", "root", "system", "llm", "brainz"}

# Extended payload structure
class CreateUserPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: Optional[EmailStr] = Field(None)
    role: Optional[str] = Field("user", description="User role (default: user)")

    @validator("username")
    def check_reserved(cls, value):
        if value.lower() in RESERVED_USERNAMES:
            raise ValueError("This username is reserved and cannot be used.")
        if not value.isalnum():
            raise ValueError("Username must be alphanumeric.")
        return value

# API endpoint to register a user
@router.post("/api/user/create")
async def create_user_endpoint(payload: CreateUserPayload, request: Request):
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")

    # Check for duplicate
    if get_user_by_name(payload.username):
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Username already exists",
                "session_id": session_id,
                "timestamp": timestamp
            }
        )

    try:
        # Create user via backend service
        api_key = create_user(payload.username)

        # Optionally log audit metadata to DB or external service
        # log_user_creation({
        #     "username": payload.username,
        #     "email": payload.email,
        #     "role": payload.role,
        #     "ip": client_ip,
        #     "agent": user_agent,
        #     "session_id": session_id,
        #     "timestamp": timestamp
        # })

        return {
            "username": payload.username,
            "api_key": api_key,
            "session_id": session_id,
            "timestamp": timestamp,
            "role": payload.role,
            "metadata": {
                "ip": client_ip,
                "user_agent": user_agent
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to create user",
                "reason": str(e),
                "session_id": session_id,
                "timestamp": timestamp
            }
        )
