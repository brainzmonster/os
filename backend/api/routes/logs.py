from fastapi import APIRouter, Query, HTTPException, Request
from fastapi.responses import StreamingResponse
from typing import Optional, Iterable, Dict, Any
from datetime import datetime
import uuid
import time
import json

from backend.utils.logger_store import get_logs  # expects advanced filtering params

router = APIRouter()


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _parse_iso(ts: Optional[str]) -> Optional[str]:
    """
    Best-effort ISO-8601 validation/normalization helper.
    Returns the original string if valid; None if empty; raises on invalid.
    We keep strings because the underlying store likely compares strings or
    parses internally. Adjust here if your store expects datetime objects.
    """
    if not ts:
        return None
    try:
        # Accept both Z-suffixed and naive ISO strings
        _ = datetime.fromisoformat(ts.replace("Z", "+00:00"))  # validate only
        return ts
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid ISO timestamp '{ts}': {e}")


def _ndjson_iter(rows: Iterable[Dict[str, Any]]) -> Iterable[str]:
    """
    Convert a list/iterator of dict log rows into an NDJSON stream generator.
    """
    for row in rows:
        yield json.dumps(row, ensure_ascii=False) + "\n"


# -----------------------------------------------------------------------------
# GET /api/system/logs — paginated logs with optional NDJSON streaming
# -----------------------------------------------------------------------------
@router.get("/api/system/logs")
async def fetch_logs(
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    level: Optional[str] = Query(None, description="Log level (e.g., INFO, ERROR, DEBUG)"),
    source: Optional[str] = Query(None, description="Subsystem name or tag"),
    start_time: Optional[str] = Query(None, description="Filter logs after ISO timestamp"),
    end_time: Optional[str] = Query(None, description="Filter logs before ISO timestamp"),
    format: Optional[str] = Query("json", description="Response format: 'json' (default) or 'ndjson'")
):
    """
    Fetch system logs with pagination, filtering, and structured output.

    Optional Parameters:
    - limit: Number of log entries to return (default: 50)
    - offset: Number of entries to skip (for pagination)
    - level: Filter by log level
    - source: Filter by log source/module
    - start_time: ISO timestamp to fetch logs after
    - end_time: ISO timestamp to fetch logs before
    - format: 'json' (default) for JSON payload, or 'ndjson' for streaming NDJSON
    """

    session_id = str(uuid.uuid4())
    start = time.time()

    # Validate/normalize timestamps early (fail-fast)
    start_time = _parse_iso(start_time)
    end_time = _parse_iso(end_time)

    try:
        logs = get_logs(
            limit=limit,
            offset=offset,
            level=level,
            source=source,
            start_time=start_time,
            end_time=end_time,
        )
        duration = round(time.time() - start, 4)

        # NDJSON streaming path (newline-delimited JSON)
        if (format or "").lower() == "ndjson":
            headers = {
                "X-Session-ID": session_id,
                "X-Response-Time": str(duration),
                "X-Timestamp": datetime.utcnow().isoformat(),
            }
            return StreamingResponse(_ndjson_iter(logs), media_type="application/x-ndjson", headers=headers)

        # Default JSON response (backwards-compatible)
        return {
            "session_id": session_id,
            "count": len(logs),
            "limit": limit,
            "offset": offset,
            "filter": {
                "level": level,
                "source": source,
                "start_time": start_time,
                "end_time": end_time,
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "response_time": duration,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent"),
            },
            "logs": logs,
        }

    except HTTPException:
        # Re-raise validation errors as-is
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to fetch logs",
                "reason": str(e),
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )


# -----------------------------------------------------------------------------
# NEW: GET /api/system/logs/stats — summarize log levels/sources for quick insights
# -----------------------------------------------------------------------------
@router.get("/api/system/logs/stats")
async def fetch_log_stats(
    level: Optional[str] = Query(None, description="Filter by log level before summarizing"),
    source: Optional[str] = Query(None, description="Filter by log source before summarizing"),
    start_time: Optional[str] = Query(None, description="Filter logs after ISO timestamp"),
    end_time: Optional[str] = Query(None, description="Filter logs before ISO timestamp"),
    limit: int = Query(1000, ge=1, le=10000),  # cap to avoid heavy scans
):
    """
    Summarize logs by level and source. Useful for dashboards and quick diagnostics.

    Returns:
    - total: total number of logs after filters
    - by_level: counts grouped by level
    - by_source: counts grouped by source
    - window: the applied time window (if any)
    """
    session_id = str(uuid.uuid4())
    start_ts = time.time()

    # Validate/normalize timestamps
    start_time = _parse_iso(start_time)
    end_time = _parse_iso(end_time)

    try:
        logs = get_logs(
            limit=limit,
            offset=0,
            level=level,
            source=source,
            start_time=start_time,
            end_time=end_time,
        )

        by_level: Dict[str, int] = {}
        by_source: Dict[str, int] = {}

        for row in logs:
            lvl = (row.get("level") or "UNKNOWN").upper()
            src = row.get("source") or "unspecified"

            by_level[lvl] = by_level.get(lvl, 0) + 1
            by_source[src] = by_source.get(src, 0) + 1

        return {
            "session_id": session_id,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "response_time": round(time.time() - start_ts, 4),
            },
            "filters": {
                "level": level,
                "source": source,
                "start_time": start_time,
                "end_time": end_time,
                "limit": limit,
            },
            "summary": {
                "total": len(logs),
                "by_level": by_level,
                "by_source": by_source,
                "window": {"start": start_time, "end": end_time},
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to summarize logs",
                "reason": str(e),
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
