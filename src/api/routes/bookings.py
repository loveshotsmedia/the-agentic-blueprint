"""
BOOKINGS API ROUTES

The dashboard reads from these endpoints to show booked jobs.
Read-only. No agent logic here.

This is what the Playwright audit tests — it books a job through
the full agent chain and then calls GET /api/bookings to confirm
the booking appears here.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from src.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_bookings(
    limit: int = Query(default=50, le=100),
    upcoming_only: bool = Query(default=False),
):
    """
    Returns all booked jobs for the dashboard.
    Ordered by job_date ascending — next upcoming jobs first.

    Optional filter: ?upcoming_only=true shows only future bookings.
    """
    db = get_db()

    try:
        query = (
            db.table("jobs")
            .select("*")
            .order("job_date", desc=False)
            .limit(limit)
        )

        if upcoming_only:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).isoformat()
            query = query.gte("job_date", now)

        result = query.execute()
        return {"bookings": result.data, "count": len(result.data)}

    except Exception as e:
        logger.error(f"Failed to fetch bookings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch bookings")


@router.get("/{call_sid}")
async def get_booking_for_call(call_sid: str):
    """
    Returns the booking created from a specific call.
    The evaluator uses this to verify a booking was created.
    The Playwright audit uses this to confirm the full chain worked.
    """
    db = get_db()

    try:
        result = (
            db.table("jobs")
            .select("*")
            .eq("call_sid", call_sid)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Booking not found")

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch booking for {call_sid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch booking")
