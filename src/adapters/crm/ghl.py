"""
GOHIGHLEVEL CRM ADAPTER

Writes job records to GoHighLevel.
Identical interface to supabase.py — that is the entire point.

The booking agent calls write_job_record().
It never knows it's talking to GHL instead of Supabase.
One env var. Same system. Different destination.

ON CAMERA TEACHING MOMENT:
"Watch this. I change one line in my .env file.
 CRM_DESTINATION=ghl
 Same call. Same agent. Same quote.
 The job just went to GoHighLevel instead of Supabase.
 I didn't change a single line of agent code."
"""

import os
import logging
import httpx

logger = logging.getLogger(__name__)

GHL_API_BASE = "https://rest.gohighlevel.com/v1"


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
    Creates a contact + opportunity in GoHighLevel.
    Returns the GHL opportunity ID on success. Returns None on failure.

    Note: GHL uses opportunities rather than a jobs table.
    The adapter translates — the booking agent never sees this difference.
    """
    api_key = os.getenv("GHL_API_KEY")
    location_id = os.getenv("GHL_LOCATION_ID")

    if not api_key or not location_id:
        logger.error("GHL_API_KEY and GHL_LOCATION_ID must be set to use GHL adapter")
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    # Parse name into first/last
    name_parts = customer_name.strip().split(" ", 1)
    first_name = name_parts[0]
    last_name = name_parts[1] if len(name_parts) > 1 else ""

    try:
        async with httpx.AsyncClient() as client:

            # Step 1: Create or update contact
            contact_response = await client.post(
                f"{GHL_API_BASE}/contacts/",
                headers=headers,
                json={
                    "firstName": first_name,
                    "lastName": last_name,
                    "phone": customer_phone,
                    "address1": address,
                    "locationId": location_id,
                    "customField": {
                        "call_sid": call_sid,
                    },
                },
            )
            contact_response.raise_for_status()
            contact_id = contact_response.json().get("contact", {}).get("id")

            if not contact_id:
                logger.error(f"GHL contact creation returned no ID for {call_sid}")
                return None

            # Step 2: Create opportunity
            opportunity_response = await client.post(
                f"{GHL_API_BASE}/pipelines/opportunities/",
                headers=headers,
                json={
                    "title": f"{issue_type.upper()} — {customer_name} — ${quote_low}-${quote_high}",
                    "contactId": contact_id,
                    "locationId": location_id,
                    "status": "open",
                    "monetaryValue": quote_high,
                    "customFields": {
                        "call_sid": call_sid,
                        "calendar_event_id": calendar_event_id,
                        "issue_type": issue_type,
                        "urgency": urgency,
                        "property_type": property_type,
                        "quote_spoken": quote_spoken,
                    },
                },
            )
            opportunity_response.raise_for_status()
            opportunity_id = opportunity_response.json().get("opportunity", {}).get("id")

            logger.info(f"Job written to GHL: {opportunity_id}")
            return opportunity_id

    except Exception as e:
        logger.error(f"GHL job write failed for {call_sid}: {e}")
        return None
