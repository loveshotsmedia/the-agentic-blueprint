"""
BOOKING AGENT

Job: Take the confirmed quote. Write to calendar. Write to Supabase. Send SMS.
     In that exact order. Always.

Contract: harness/contracts/booking.json
Trust tier: 4 — WRITE EXTERNAL (highest trust — has real external side effects)

EXECUTION ORDER — NON-NEGOTIABLE:
1. Read plan file and quote file from state/artifacts/
2. Write to Google Calendar (or GHL calendar)
3. Confirm calendar_event_id — if empty, HALT (Level 3 failure)
4. Write job record to Supabase (or GHL CRM)
5. Confirm supabase_job_id — if empty, log but continue
6. Send SMS confirmation to caller
7. Write booking file to state/artifacts/
8. Trigger evaluator

WHY CALENDAR BEFORE SUPABASE:
The calendar is the source of truth for when the technician shows up.
If only Supabase writes and the calendar fails — the technician has no record.
Calendar first. Always.
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


async def run_booking_agent(call_sid: str) -> dict:
    """
    Main entry point. Called by the quote agent when a valid quote exists.
    """
    logger.info(f"Booking agent starting for call: {call_sid}")

    # ── Read the plan and quote files ───────────────────────────────────────
    plan_path = f"state/artifacts/{call_sid}-plan.json"
    quote_path = f"state/artifacts/{call_sid}-quote.json"

    try:
        with open(plan_path) as f:
            plan = json.load(f)
        with open(quote_path) as f:
            quote = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Artifact file not found: {e}")
        return await _write_failure_booking(call_sid, f"artifact_not_found: {e}")

    # ── Import the correct adapters based on env vars ───────────────────────
    # This is the adapter pattern — one env var routes to the right destination
    crm_destination = os.getenv("CRM_DESTINATION", "supabase")
    calendar_destination = os.getenv("CALENDAR_DESTINATION", "google")

    if calendar_destination == "google":
        from src.adapters.calendar.google import write_calendar_event
    else:
        from src.adapters.calendar.ghl_calendar import write_calendar_event

    if crm_destination == "supabase":
        from src.adapters.crm.supabase import write_job_record
    else:
        from src.adapters.crm.ghl import write_job_record

    # ── Step 2: Write to calendar ───────────────────────────────────────────
    logger.info(f"Writing to {calendar_destination} calendar for {call_sid}")

    try:
        calendar_event_id = await write_calendar_event(
            customer_name=plan["name"],
            address=plan["address"],
            issue_type=plan["issue_type"],
            urgency=plan["urgency"],
            quote_low=quote["price_low"],
            quote_high=quote["price_high"],
            call_sid=call_sid,
        )
    except Exception as e:
        logger.error(f"Calendar write failed for {call_sid}: {e}")
        calendar_event_id = None

    # ── Step 3: Verify calendar write ──────────────────────────────────────
    if not calendar_event_id:
        logger.critical(
            f"LEVEL 3 DATA INTEGRITY FAILURE: "
            f"Calendar write returned no event ID for {call_sid}. "
            f"Halting — not writing to Supabase, not sending SMS."
        )
        return await _write_data_integrity_failure(
            call_sid=call_sid,
            stage="calendar_write",
            plan=plan,
            quote=quote,
        )

    logger.info(f"Calendar event created: {calendar_event_id}")

    # ── Step 4: Write to CRM ────────────────────────────────────────────────
    logger.info(f"Writing to {crm_destination} for {call_sid}")

    try:
        job_id = await write_job_record(
            call_sid=call_sid,
            calendar_event_id=calendar_event_id,
            customer_name=plan["name"],
            customer_phone=plan["caller_phone"],
            address=plan["address"],
            issue_type=plan["issue_type"],
            urgency=plan["urgency"],
            property_type=plan["property_type"],
            quote_low=quote["price_low"],
            quote_high=quote["price_high"],
            quote_spoken=quote["quote_spoken_text"],
        )
    except Exception as e:
        logger.error(f"CRM write failed for {call_sid}: {e}")
        job_id = None

    # ── Step 5: Verify CRM write (non-blocking) ─────────────────────────────
    if not job_id:
        logger.warning(
            f"CRM write returned no job ID for {call_sid}. "
            f"Continuing to SMS — manual CRM entry may be needed."
        )

    # ── Step 6: Send SMS confirmation ───────────────────────────────────────
    logger.info(f"Sending SMS confirmation to {plan.get('caller_phone')} for {call_sid}")

    from src.adapters.sms import send_sms_confirmation

    sms_message_sid = None
    sms_delivered = False

    for sms_attempt in range(2):
        try:
            sms_message_sid = await send_sms_confirmation(
                to_phone=plan["caller_phone"],
                customer_name=plan["name"],
                issue_type=plan["issue_type"],
                job_date="Scheduled — details to follow",
                job_time="Your technician will confirm the exact time",
                address=plan["address"],
            )
            sms_delivered = True
            logger.info(f"SMS sent: {sms_message_sid}")
            break

        except Exception as e:
            logger.warning(f"SMS attempt {sms_attempt + 1} failed for {call_sid}: {e}")

    if not sms_delivered:
        logger.error(
            f"SMS failed after 2 attempts for {call_sid}. "
            f"Booking is complete but customer needs manual follow-up."
        )

    # ── Step 7: Write booking artifact ─────────────────────────────────────
    booking = {
        "call_sid": call_sid,
        "calendar_event_id": calendar_event_id,
        "calendar_destination": calendar_destination,
        "supabase_job_id": job_id,
        "crm_destination": crm_destination,
        "sms_message_sid": sms_message_sid,
        "sms_delivered": sms_delivered,
        "customer_name": plan["name"],
        "customer_address": plan["address"],
        "issue_type": plan["issue_type"],
        "quote_low": quote["price_low"],
        "quote_high": quote["price_high"],
        "booked_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    Path("state/artifacts").mkdir(parents=True, exist_ok=True)
    booking_path = f"state/artifacts/{call_sid}-booking.json"

    with open(booking_path, "w") as f:
        json.dump(booking, f, indent=2)

    logger.info(f"Booking artifact written: {booking_path}")

    # ── Update plan file to mark stage 3 complete ───────────────────────────
    plan["stage_3_booking_ready"] = True
    with open(f"state/artifacts/{call_sid}-plan.json", "w") as f:
        json.dump(plan, f, indent=2)

    # ── Step 8: Trigger evaluator ───────────────────────────────────────────
    from src.agents.evaluator import run_evaluator
    await run_evaluator(call_sid=call_sid)

    return booking


async def _write_data_integrity_failure(
    call_sid: str,
    stage: str,
    plan: dict,
    quote: dict,
) -> dict:
    """
    Level 3 failure — data integrity issue.
    Written to state/decisions/ not state/traces/
    because this requires human review and a decision.
    """
    Path("state/decisions").mkdir(parents=True, exist_ok=True)

    decision_entry = {
        "type": "data_integrity_failure",
        "call_sid": call_sid,
        "stage": stage,
        "customer_name": plan.get("name"),
        "customer_phone": plan.get("caller_phone"),
        "address": plan.get("address"),
        "issue_type": plan.get("issue_type"),
        "quote_low": quote.get("price_low"),
        "quote_high": quote.get("price_high"),
        "action_required": "Manual calendar entry and customer contact needed",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    filename = f"state/decisions/{call_sid}-data-integrity-{stage}.json"
    with open(filename, "w") as f:
        json.dump(decision_entry, f, indent=2)

    logger.critical(f"Data integrity failure recorded: {filename}")
    return {"call_sid": call_sid, "error": "data_integrity_failure", "stage": stage}


async def _write_failure_booking(call_sid: str, reason: str) -> dict:
    """Standard failure trace for recoverable errors."""
    Path("state/traces").mkdir(parents=True, exist_ok=True)

    trace = {
        "call_sid": call_sid,
        "error": reason,
        "stage": "booking_agent",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(f"state/traces/{call_sid}-booking-failure.jsonl", "a") as f:
        f.write(json.dumps(trace) + "\n")

    logger.error(f"Booking failure trace written for {call_sid}: {reason}")
    return {"call_sid": call_sid, "error": reason}
