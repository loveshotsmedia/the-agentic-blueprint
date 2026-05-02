"""
GOOGLE CALENDAR ADAPTER

Writes booking events to Google Calendar.
Same interface as ghl_calendar.py — swap the env var, system reroutes.
"""

import os
import logging
from datetime import datetime, timezone, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_calendar_service():
    """
    Builds and returns an authenticated Google Calendar service.
    Uses the service account credentials file from .env.
    """
    credentials_file = os.getenv(
        "GOOGLE_SERVICE_ACCOUNT_FILE",
        "credentials/google-service-account.json"
    )

    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=SCOPES,
    )

    return build("calendar", "v3", credentials=credentials)


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
    Creates a calendar event for the booked job.
    Returns the Google Calendar event ID on success. Returns None on failure.

    If no job_datetime provided — defaults to next business day at 9am.
    In production the voice agent collects the preferred slot from the caller.
    """
    calendar_id = os.getenv("GOOGLE_CALENDAR_ID")

    if not calendar_id:
        logger.error("GOOGLE_CALENDAR_ID must be set")
        return None

    # Default to next business day 9am if no slot collected yet
    if not job_datetime:
        job_datetime = datetime.now(timezone.utc) + timedelta(days=1)
        job_datetime = job_datetime.replace(hour=9, minute=0, second=0, microsecond=0)

    job_end = job_datetime + timedelta(hours=2)

    event_body = {
        "summary": f"{issue_type.upper()} — {customer_name}",
        "location": address,
        "description": (
            f"Customer: {customer_name}\n"
            f"Issue: {issue_type}\n"
            f"Urgency: {urgency}\n"
            f"Quote: ${quote_low}–${quote_high}\n"
            f"Call SID: {call_sid}\n"
            f"Booked via: Rich Off AI HVAC"
        ),
        "start": {
            "dateTime": job_datetime.isoformat(),
            "timeZone": os.getenv("TIMEZONE", "America/New_York"),
        },
        "end": {
            "dateTime": job_end.isoformat(),
            "timeZone": os.getenv("TIMEZONE", "America/New_York"),
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "email", "minutes": 24 * 60},
                {"method": "popup", "minutes": 60},
            ],
        },
    }

    try:
        service = _get_calendar_service()
        event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
        ).execute()

        event_id = event.get("id")
        logger.info(f"Google Calendar event created: {event_id}")
        return event_id

    except Exception as e:
        logger.error(f"Google Calendar write failed for {call_sid}: {e}")
        return None
