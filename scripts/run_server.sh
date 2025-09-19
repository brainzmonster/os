#!/bin/bash

# === brainzOS Server Startup Script ===
# Author: Core Maintainer
# Version: 1.2

# ------------------------------------------------------------------------------
# Purpose:
#   Start the FastAPI server (Uvicorn) for brainzOS with sane defaults.
#   Adds a smart port resolver that can auto-pick a free port when requested.
#   Keeps full backward compatibility with existing flags/behavior.
# ------------------------------------------------------------------------------

# Generate UUID session ID + UTC timestamp for traceability
SESSION_ID=$(uuidgen)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# Default runtime options
RELOAD="--reload"            # hot-reload by default (dev mode)
LOG_FILE=""                  # optional tee log file
MODE="dev"                   # dev|prod
HOST="0.0.0.0"               # default host
PORT="8000"                  # default port
AUTO_PORT="false"            # when true, scan for free port starting at $PORT

# ------------------------------------------------------------------------------
# NEW: Port/Host utilities
# ------------------------------------------------------------------------------

# Check if a port is already in use (tries 'ss' first, falls back to 'lsof')
is_port_in_use() {
  local _port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -ltn 2>/dev/null | awk '{print $4}' | grep -qE ":${_port}\b"
    return $?
  elif command -v lsof >/dev/null 2>&1; then
    lsof -iTCP -sTCP:LISTEN -P 2>/dev/null | awk '{print $9}' | grep -qE ":${_port}\b"
    return $?
  else
    # Fallback: try a netcat zero-connect if available
    if command -v nc >/dev/null 2>&1; then
      nc -z 127.0.0.1 "${_port}" >/dev/null 2>&1
      return $?
    fi
    # If we cannot detect, assume it's free
    return 1
  fi
}

# Resolve a usable port:
# - If AUTO_PORT=false -> just return the requested base port (keeps old behavior)
# - If AUTO_PORT=true  -> find the first free port starting at base port (max +50)
resolve_port() {
  local _base="${1:-8000}"
  if [ "$AUTO_PORT" != "true" ]; then
    echo "$_base"
    return 0
  fi

  local _max_increments=50
  local _try=0
  while [ "$_try" -le "$_max_increments" ]; do
    local _candidate=$(( _base + _try ))
    if ! is_port_in_use "$_candidate"; then
      echo "$_candidate"
      return 0
    fi
    _try=$(( _try + 1 ))
  done

  # Fallback: if none free in range, return base anyway
  echo "$_base"
}

# ------------------------------------------------------------------------------
# Parse command-line flags
# ------------------------------------------------------------------------------
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
    --host=*)
      HOST="${arg#*=}"
      shift
      ;;
    --port=*)
      PORT="${arg#*=}"
      shift
      ;;
    --auto-port)
      AUTO_PORT="true"
      shift
      ;;
    *)
      ;; # ignore unknown flags to remain backward compatible
  esac
done

# ------------------------------------------------------------------------------
# Print banner
# ------------------------------------------------------------------------------
echo ""
echo "──────────────────────────────────────────────"
echo "🧠 [brainzOS] Launching API Server"
echo "📅 Timestamp: $TIMESTAMP"
echo "🔐 Session ID: $SESSION_ID"
echo "🌐 Mode: $MODE"
echo "🔌 Host: $HOST"
echo "🔢 Base Port: $PORT  (auto-port: $AUTO_PORT)"
echo "──────────────────────────────────────────────"
echo ""

# Auto-create .env if missing (keeps local DX smooth)
if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  echo "[i] No .env found. Creating from .env.example..."
  cp .env.example .env
fi

# Activate virtual environment if present
if [ -d "venv" ]; then
  echo "[✓] Activating virtual environment"
  # shellcheck disable=SC1091
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

# Resolve final port (may auto-increment if --auto-port was passed)
FINAL_PORT="$(resolve_port "$PORT")"
if [ "$FINAL_PORT" != "$PORT" ]; then
  echo "[i] Port $PORT is busy. Using free port: $FINAL_PORT"
fi

# Launch Uvicorn with optional logging
echo "[✓] Starting FastAPI server on $HOST:$FINAL_PORT ..."
if [ -n "$LOG_FILE" ]; then
  # Tee logs to file + stdout for observability
  uvicorn "$UVICORN_CMD" --host "$HOST" --port "$FINAL_PORT" $RELOAD 2>&1 | tee "$LOG_FILE"
else
  uvicorn "$UVICORN_CMD" --host "$HOST" --port "$FINAL_PORT" $RELOAD
fi

# Capture exit code and exit cleanly
EXIT_CODE=$?
echo ""
echo "[✓] Server exited with status code $EXIT_CODE"
exit $EXIT_CODE
