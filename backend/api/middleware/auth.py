from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from backend.services.user_service import get_user_by_key
import time
import logging

logger = logging.getLogger("brainz.auth")


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that checks for a valid API key in request headers.
    If the key is missing or invalid, the request is blocked.
    """

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        api_key = request.headers.get("X-API-Key")

        # Reject requests without an API key
        if not api_key:
            logger.warning("[Auth] Missing API key")
            raise HTTPException(status_code=401, detail="Missing API key")

        # Validate the API key via DB lookup
        user = get_user_by_key(api_key)
        if not user:
            logger.warning("[Auth] Invalid API key")
            raise HTTPException(status_code=403, detail="Invalid API key")

        # Attach user to request state for downstream use
        request.state.user = user
        response = await call_next(request)

        # Log request latency for debugging or analytics
        duration = round((time.time() - start_time) * 1000, 2)
        logger.info(f"[Auth] Request authorized for user={user.username} ({duration}ms)")

        return response


# -----------------------------------------------------------------------------
# NEW: Middleware utility to verify user role access (e.g., admin-only routes)
# -----------------------------------------------------------------------------
async def verify_admin_access(request: Request):
    """
    Checks if the authenticated user has admin privileges.
    Can be used as a dependency or middleware hook for protected endpoints.
    Raises HTTP 403 if user lacks permissions.

    Example usage in a route:
    ```python
    from fastapi import Depends
    from backend.api.middleware import verify_admin_access

    @router.get("/admin/data", dependencies=[Depends(verify_admin_access)])
    async def get_admin_data():
        return {"status": "ok"}
    ```
    """
    user = getattr(request.state, "user", None)

    # If user is not authenticated
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # If user model has `is_admin` attribute, check it
    if hasattr(user, "is_admin") and not getattr(user, "is_admin"):
        logger.warning(f"[Auth] Unauthorized admin access attempt by {user.username}")
        raise HTTPException(status_code=403, detail="Admin privileges required")

    # If user model lacks `is_admin`, assume restricted access
    elif not hasattr(user, "is_admin"):
        logger.warning(f"[Auth] User {user.username} lacks admin role attribute")
        raise HTTPException(status_code=403, detail="Role not defined for admin access")

    # Access granted
    logger.info(f"[Auth] Admin access verified for user={user.username}")
    return True
