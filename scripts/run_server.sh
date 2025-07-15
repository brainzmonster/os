#!/bin/bash

# === brainzOS Server Startup Script ===
# Author: Core Maintainer
# Version: 1.1

# Generate UUID session ID
SESSION_ID=$(uuidgen)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Optional flags
RELOAD="--reload"
LOG_FILE=""
MODE="dev"

# Parse command-line flags
for arg in "$@"; do
  case $arg in
    --prod)
      MODE="prod"
      RELOAD=""
      shift
      ;;
    --no-reload)
      RELOAD=""
      shift
      ;;
    --log=*)
      LOG_FILE="${arg#*=}"
      shift
      ;;
    *)
      ;;
  esac
done

# Print banner
echo ""
echo "──────────────────────────────────────────────"
echo "🧠 [brainzOS] Launching API Server"
echo "📅 Timestamp: $TIMESTAMP"
echo "🔐 Session ID: $SESSION_ID"
echo "🌐 Mode: $MODE"
echo "──────────────────────────────────────────────"
echo ""

# Auto-create .env if missing
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "[i] No .env found. Creating from .env.example..."
  cp .env.example .env
fi

# Activate virtual environment
if [ -d "venv" ]; then
  echo "[✓] Activating virtual environment"
  source venv/bin/activate
fi

# Export PYTHONPATH for absolute imports
export PYTHONPATH=.

# Set Uvicorn app entrypoint
export UVICORN_CMD="backend.api.server:app"

# Check if uvicorn is installed
if ! command -v uvicorn &> /dev/null; then
  echo "[✗] Uvicorn is not installed. Run: pip install uvicorn"
  exit 1
fi

# Launch Uvicorn with optional logging
echo "[✓] Starting FastAPI server..."
if [ -n "$LOG_FILE" ]; then
  uvicorn $UVICORN_CMD --host 0.0.0.0 --port 8000 $RELOAD 2>&1 | tee "$LOG_FILE"
else
  uvicorn $UVICORN_CMD --host 0.0.0.0 --port 8000 $RELOAD
fi

# Exit clean
EXIT_CODE=$?
echo ""
echo "[✓] Server exited with status code $EXIT_CODE"
exit $EXIT_CODE
