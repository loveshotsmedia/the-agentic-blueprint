"""
GOHIGHLEVEL CALENDAR ADAPTER

Writes booking events to GoHighLevel calendar.
Identical interface to google.py — that is the entire point.

The booking agent calls write_calendar_event().
It never knows it's talking to GHL instead of Google.
One env var. Same system. Different destination.

CALENDAR_DESTINATION=ghl_calendar  ← this file runs
CALENDAR_DESTINATION=google        ← google.py runs
"""

import os
import logging
from datetime import datetime, timezone, timedelta
import httpx

logger = logging.getLogger(__name__)

GHL_API_BASE = "https://rest.gohighlevel.com/v1"


async def write_calendar_event(
    customer_name: str,
    address: str,
    issue_type: str,
    urgency: str,
    quote_low: float,
    quote_high: float,
    call_sid: str,
    job_datetime: datetime = None,
) -> str | None:
    """
    Creates a calendar appointment in GoHighLevel.
    Returns the GHL appointment ID on success. Returns None on failure.

    Identical function signature to google.py.
    The booking agent cannot tell which adapter it's using.
    That is the design.
    """
    api_key = os.getenv("GHL_API_KEY")
    location_id = os.getenv("GHL_LOCATION_ID")
    calendar_id = os.getenv("GHL_CALENDAR_ID")

    if not all([api_key, location_id, calendar_id]):
        logger.error(
            "GHL_API_KEY, GHL_LOCATION_ID, and GHL_CALENDAR_ID "
            "must all be set to use the GHL calendar adapter"
        )
        return None

    if not job_datetime:
        job_datetime = datetime.now(timezone.utc) + timedelta(days=1)
        job_datetime = job_datetime.replace(hour=9, minute=0, second=0, microsecond=0)

    job_end = job_datetime + timedelta(hours=2)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    appointment_body = {
        "calendarId": calendar_id,
        "locationId": location_id,
        "title": f"{issue_type.upper()} — {customer_name}",
        "appointmentStatus": "confirmed",
        "startTime": job_datetime.isoformat(),
        "endTime": job_end.isoformat(),
        "address": address,
        "notes": (
            f"Customer: {customer_name}\n"
            f"Issue: {issue_type}\n"
            f"Urgency: {urgency}\n"
            f"Quote: ${quote_low}–${quote_high}\n"
            f"Call SID: {call_sid}\n"
            f"Booked via: Rich Off AI HVAC"
        ),
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GHL_API_BASE}/appointments/",
                headers=headers,
                json=appointment_body,
            )
            response.raise_for_status()

            appointment_id = response.json().get("appointment", {}).get("id")

            if not appointment_id:
                logger.error(f"GHL calendar returned no appointment ID for {call_sid}")
                return None

            logger.info(f"GHL calendar event created: {appointment_id}")
            return appointment_id

    except Exception as e:
        logger.error(f"GHL calendar write failed for {call_sid}: {e}")
        return None
