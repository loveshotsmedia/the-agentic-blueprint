"""
SUPABASE CRM ADAPTER

Writes job records to Supabase.
Same interface as ghl.py — swap the env var, system reroutes.

This is the adapter pattern made real.
The booking agent calls write_job_record().
It never knows whether it's talking to Supabase or GHL.
The adapter handles the translation.
"""

import os
import logging
from src.database import get_db

logger = logging.getLogger(__name__)


async def write_job_record(
    call_sid: str,
    calendar_event_id: str,
    customer_name: str,
    customer_phone: str,
    address: str,
    issue_type: str,
    urgency: str,
    property_type: str,
    quote_low: float,
    quote_high: float,
    quote_spoken: str,
) -> str | None:
    """
    Writes a job record to the Supabase jobs table.
    Returns the job UUID on success. Returns None on failure.
    """
    db = get_db()

    try:
        result = db.table("jobs").insert({
            "call_sid": call_sid,
            "calendar_event_id": calendar_event_id,
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "address": address,
            "issue_type": issue_type,
            "urgency": urgency,
            "property_type": property_type,
            "quote_low": quote_low,
            "quote_high": quote_high,
            "quote_spoken": quote_spoken,
            "status": "booked",
            "source": "inbound_call",
        }).execute()

        if result.data:
            job_id = result.data[0]["id"]
            logger.info(f"Job written to Supabase: {job_id}")
            return job_id

        return None

    except Exception as e:
        logger.error(f"Supabase job write failed for {call_sid}: {e}")
        return None
