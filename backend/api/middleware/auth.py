from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.user_service import get_user_by_key

class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            raise HTTPException(status_code=401, detail="Missing API key")

        user = get_user_by_key(api_key)
        if not user:
            raise HTTPException(status_code=403, detail="Invalid API key")

        request.state.user = user
        response = await call_next(request)
        return response