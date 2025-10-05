from fastapi.middleware.cors import CORSMiddleware
import logging

logger = logging.getLogger("brainz.cors")


# -----------------------------------------------------------------------------
# Core CORS setup — allows frontend and API to communicate across domains
# -----------------------------------------------------------------------------
def setup_cors(app):
    """
    Configure global CORS policy for the FastAPI app.
    By default, all origins, methods, and headers are allowed.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],          # Allow all origins (for dev/demo)
        allow_credentials=True,       # Enable cookies/credentials
        allow_methods=["*"],          # Allow all HTTP methods (GET, POST, etc.)
        allow_headers=["*"],          # Allow all request headers
    )
    logger.info("[CORS] Default CORS policy applied — all origins allowed.")


# -----------------------------------------------------------------------------
# NEW FUNCTION: Dynamic CORS configuration loader
# -----------------------------------------------------------------------------
def update_cors_policy(app, allowed_origins: list[str]):
    """
    Dynamically reconfigure the app's CORS middleware at runtime.
    This is useful when moving from development (open access)
    to production (restricted domain list).

    Args:
        app: FastAPI app instance
        allowed_origins (list[str]): List of domains allowed to access the API

    Example:
    ```python
    from backend.api.cors import update_cors_policy
    update_cors_policy(app, ["https://brainz.monster", "https://app.brainz.monster"])
    ```
    """
    # Remove existing CORSMiddleware instances
    new_stack = []
    for middleware in app.user_middleware:
        if middleware.cls.__name__ != "CORSMiddleware":
            new_stack.append(middleware)
    app.user_middleware = new_stack

    # Apply new, restricted policy
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS", "PUT"],
        allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    )

    logger.info(f"[CORS] Updated policy applied — allowed origins: {allowed_origins}")
