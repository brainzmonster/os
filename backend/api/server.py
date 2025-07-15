# FastAPI core import to create the web application instance
from fastapi import FastAPI

# CORS middleware to allow cross-origin requests (required for frontend access)
from fastapi.middleware.cors import CORSMiddleware

# Import API route modules
from backend.api.routes import llm, train, logs, user

# Lifecycle hooks for app startup and shutdown (DB/model loading)
from backend.core.lifecycle import on_startup, on_shutdown


# Create FastAPI instance with a custom title
app = FastAPI(title="brainz OS API")

# Configure CORS settings (allow all origins for development)
# In production, restrict origins to allowed domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register startup hook for initializing model, DB, etc.
@app.on_event("startup")
async def startup_event():
    on_startup()

# Register shutdown hook for cleanup tasks
@app.on_event("shutdown")
async def shutdown_event():
    on_shutdown()

# Register all route modules with the application
app.include_router(llm.router)
app.include_router(train.router)
app.include_router(logs.router)
app.include_router(user.router)

# Root endpoint for health check / welcome message
@app.get("/")
async def root():
    return {"message": "brainz OS is running."}
