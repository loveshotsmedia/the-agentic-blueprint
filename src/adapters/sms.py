"""
SMS ADAPTER — Twilio

Sends confirmation texts to customers after booking.
Called by the booking agent after calendar + CRM writes succeed.

The message must be under 320 characters (2 SMS segments).
Always includes: customer name, job details, business callback number.
"""

import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)


async def send_sms_confirmation(
    to_phone: str,
    customer_name: str,
    issue_type: str,
    job_date: str,
    job_time: str,
    address: str,
) -> str | None:
    """
    Sends an SMS booking confirmation to the customer.
    Returns the Twilio message SID on success. Returns None on failure.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_FROM_NUMBER")
    business_name = os.getenv("BUSINESS_NAME", "Rich Off AI HVAC")
    business_phone = os.getenv("BUSINESS_PHONE", "")

    if not all([account_sid, auth_token, from_number]):
        logger.error("Twilio credentials not configured")
        return None

    first_name = customer_name.split()[0] if customer_name else "there"

    message_body = (
        f"Hi {first_name}, your {issue_type} appointment is confirmed.\n"
        f"📅 {job_date} at {job_time}\n"
        f"📍 {address}\n"
        f"Questions? Call {business_name}: {business_phone}"
    )

    # Keep under 320 characters
    if len(message_body) > 320:
        message_body = message_body[:317] + "..."

    try:
        client = Client(account_sid, auth_token)

        message = client.messages.create(
            body=message_body,
            from_=from_number,
            to=to_phone,
        )

        logger.info(f"SMS sent to {to_phone}: {message.sid}")
        return message.sid

    except Exception as e:
        logger.error(f"SMS send failed to {to_phone}: {e}")
        return None
