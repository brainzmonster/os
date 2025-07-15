from fastapi import APIRouter, Query, HTTPException, Request
from backend.utils.logger_store import get_logs
from typing import Optional
from datetime import datetime
import uuid
import time

router = APIRouter()


@router.get("/api/system/logs")
async def fetch_logs(
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    level: Optional[str] = Query(None, description="Log level (e.g., INFO, ERROR, DEBUG)"),
    source: Optional[str] = Query(None, description="Subsystem name or tag"),
    start_time: Optional[str] = Query(None, description="Filter logs after ISO timestamp"),
    end_time: Optional[str] = Query(None, description="Filter logs before ISO timestamp")
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
    """

    session_id = str(uuid.uuid4())
    start = time.time()

    try:
        logs = get_logs(
            limit=limit,
            offset=offset,
            level=level,
            source=source,
            start_time=start_time,
            end_time=end_time
        )

        duration = round(time.time() - start, 4)

        return {
            "session_id": session_id,
            "count": len(logs),
            "limit": limit,
            "offset": offset,
            "filter": {
                "level": level,
                "source": source,
                "start_time": start_time,
                "end_time": end_time
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "response_time": duration,
                "client_ip": request.client.host,
                "user_agent": request.headers.get("user-agent")
            },
            "logs": logs
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Failed to fetch logs",
                "reason": str(e),
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
