# FastAPI core import to create the web application instance
from fastapi import FastAPI

# CORS middleware to allow cross-origin requests (required for frontend access)
from fastapi.middleware.cors import CORSMiddleware

# Import API route modules
from backend.api.routes import llm, train, logs, user

# Lifecycle hooks for app startup and shutdown (DB/model loading)
from backend.core.lifecycle import on_startup, on_shutdown

# Logging setup
import logging
logger = logging.getLogger("brainz.api")


# -----------------------------------------------------------------------------
# Create FastAPI instance with a custom title
# -----------------------------------------------------------------------------
app = FastAPI(title="brainz OS API")

# -----------------------------------------------------------------------------
# Configure CORS settings (allow all origins for development)
# In production, restrict origins to allowed domains
# -----------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Allow all origins for development
    allow_credentials=True,       # Enable credentials (cookies, auth headers)
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Allow all custom headers
)

# -----------------------------------------------------------------------------
# Application lifecycle events — startup and shutdown hooks
# -----------------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """
    Called when the FastAPI server starts.
    Handles initialization of database, model loading, etc.
    """
    logger.info("[brainzOS] Startup event triggered.")
    on_startup()

@app.on_event("shutdown")
async def shutdown_event():
    """
    Called when the FastAPI server is shutting down.
    Handles cleanup tasks and resource deallocation.
    """
    logger.info("[brainzOS] Shutdown event triggered.")
    on_shutdown()


# -----------------------------------------------------------------------------
# Register all route modules with the application
# -----------------------------------------------------------------------------
app.include_router(llm.router)
app.include_router(train.router)
app.include_router(logs.router)
app.include_router(user.router)


# -----------------------------------------------------------------------------
# Root endpoint for health check / welcome message
# -----------------------------------------------------------------------------
@app.get("/")
async def root():
    """
    Basic root endpoint to confirm that the API is operational.
    Useful for uptime checks and monitoring tools.
    """
    return {"message": "brainz OS is running."}


# -----------------------------------------------------------------------------
# NEW FUNCTION: Health check endpoint with extended diagnostics
# -----------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    """
    Returns a detailed system health report for debugging or monitoring.
    This endpoint can be used by uptime monitors or CI/CD pipelines.
    """
    from backend.core.engine import engine

    model_loaded = engine.get_model().get("model") is not None
    db_connected = engine.get_db() is not None

    status = {
        "status": "ok" if model_loaded and db_connected else "degraded",
        "model_loaded": model_loaded,
        "db_connected": db_connected,
        "version": "1.0.0",
        "uptime": "active",
    }

    logger.info(f"[HealthCheck] Status: {status}")
    return status
