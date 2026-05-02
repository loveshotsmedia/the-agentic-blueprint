"""
QUOTES API ROUTES

The dashboard reads from these endpoints to show generated quotes.
Read-only. No agent logic here.
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from src.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_quotes(
    limit: int = Query(default=50, le=100),
):
    """
    Returns all generated quotes for the dashboard.
    Ordered by most recent first.
    """
    db = get_db()

    try:
        result = (
            db.table("quotes")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"quotes": result.data, "count": len(result.data)}

    except Exception as e:
        logger.error(f"Failed to fetch quotes: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch quotes")


@router.get("/{call_sid}")
async def get_quote_for_call(call_sid: str):
    """
    Returns the quote generated for a specific call.
    """
    db = get_db()

    try:
        result = (
            db.table("quotes")
            .select("*")
            .eq("call_sid", call_sid)
            .single()
            .execute()
        )

        if not result.data:
            raise HTTPException(status_code=404, detail="Quote not found")

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch quote for {call_sid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch quote")
