from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, EmailStr, validator
from backend.services.user_service import create_user, get_user_by_name, get_active_users
from datetime import datetime
import uuid
from typing import Optional, List

router = APIRouter()

# Reserved usernames (can be expanded as needed)
RESERVED_USERNAMES = {"admin", "root", "system", "llm", "brainz"}

# -----------------------------------------------------------------------------
# Pydantic model for user creation payload
# -----------------------------------------------------------------------------
class CreateUserPayload(BaseModel):
    username: str = Field(..., min_length=3, max_length=32)
    email: Optional[EmailStr] = Field(None)
    role: Optional[str] = Field("user", description="User role (default: user)")

    # Validator ensures usernames are valid and not reserved
    @validator("username")
    def check_reserved(cls, value):
        if value.lower() in RESERVED_USERNAMES:
            raise ValueError("This username is reserved and cannot be used.")
        if not value.isalnum():
            raise ValueError("Username must be alphanumeric.")
        return value


# -----------------------------------------------------------------------------
# POST /api/user/create — Create a new user
# -----------------------------------------------------------------------------
@router.post("/api/user/create")
async def create_user_endpoint(payload: CreateUserPayload, request: Request):
    """
    Register a new user and automatically generate an API key.
    Includes IP and User-Agent tracking for auditing.
    """
    session_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().isoformat()
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent")

    # Check for duplicate usernames
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
        result = create_user(payload.username, email=payload.email)

        return {
            "username": result["username"],
            "api_key": result["api_key"],
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


# -----------------------------------------------------------------------------
# NEW FUNCTION: GET /api/user/active — List active users
# -----------------------------------------------------------------------------
@router.get("/api/user/active")
async def list_active_users(limit: int = 50):
    """
    Returns a list of currently active users, limited by query parameter.
    Useful for admin dashboards or usage monitoring.
    """
    try:
        users = get_active_users(limit=limit)
        if not users:
            return {"message": "No active users found.", "count": 0, "users": []}

        data = [
            {
                "id": u.id,
                "username": u.username,
                "created_at": u.created_at.isoformat(),
                "is_active": u.is_active,
            }
            for u in users
        ]
        return {"count": len(data), "users": data}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to retrieve active users",
                "reason": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
