"""
CALLS API ROUTES

The dashboard reads from these endpoints to show call history.
Read-only. No agent logic here.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from src.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_calls(
    limit: int = Query(default=50, le=100),
    status: str = Query(default=None),
):
    """
    Returns call history for the dashboard.
    The dashboard calls this on page load and polls every 30 seconds.

    Optional filter: ?status=completed | processing | failed | in_progress
    """
    db = get_db()

    try:
        query = db.table("calls").select("*").order("created_at", desc=True).limit(limit)

        if status:
            query = query.eq("status", status)

        result = query.execute()
        return {"calls": result.data, "count": len(result.data)}

    except Exception as e:
        logger.error(f"Failed to fetch calls: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch calls")


@router.get("/{call_sid}")
async def get_call(call_sid: str):
    """
    Returns a single call record with full transcript.
    The dashboard uses this when an advisor clicks on a call to review it.
    """
    db = get_db()

    try:
        result = db.table("calls").select("*").eq("call_sid", call_sid).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Call not found")

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch call {call_sid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch call")
