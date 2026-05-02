"""
VAPI WEBHOOK RECEIVER

This is where every phone call enters the system.

When someone calls the Rich Off AI HVAC number:
1. Vapi handles the voice conversation
2. Vapi sends events to this endpoint as the call progresses
3. This file receives those events
4. When the call has enough data — it triggers the planner agent

WHAT THIS FILE DOES:
- Receives webhook events from Vapi
- Verifies the webhook signature (security — rejects fake requests)
- Routes each event type to the right handler
- Triggers the agent chain when a call ends

WHAT THIS FILE DOES NOT DO:
- Does not generate quotes (that is the quote agent's job)
- Does not write to the calendar (that is the booking agent's job)
- Does not evaluate anything (that is the evaluator's job)

Each agent has exactly one job. This file's job is to receive and route.
"""

import os
import hmac
import hashlib
import logging
import json
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional

from src.agents.planner import run_planner
from src.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Event schemas ─────────────────────────────────────────────────────────────
# These match the shapes Vapi sends us.
# Pydantic validates every incoming request against these schemas.
# If Vapi sends something unexpected — we know immediately.

class VapiCallData(BaseModel):
    call_sid: str
    caller_phone: str
    transcript: Optional[str] = None
    status: Optional[str] = None
    duration_seconds: Optional[int] = None
    assistant_id: Optional[str] = None


class VapiWebhookEvent(BaseModel):
    type: str                           # call.started | call.ended | transcript.update
    call: VapiCallData
    timestamp: Optional[str] = None


# ── Signature verification ────────────────────────────────────────────────────
def verify_vapi_signature(payload: bytes, signature: str) -> bool:
    """
    Vapi signs every webhook request with your VAPI_WEBHOOK_SECRET.
    This function verifies that the request actually came from Vapi
    and not from someone trying to fake a call event.

    If this check fails — the request is rejected with a 401.
    Security first. Always.
    """
    secret = os.getenv("VAPI_WEBHOOK_SECRET", "")
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


# ── Main webhook endpoint ─────────────────────────────────────────────────────
@router.post("/vapi")
async def vapi_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Vapi sends all call events here.
    Every call that comes in through the Rich Off AI HVAC number
    will trigger this endpoint multiple times:
    - Once when the call starts
    - Once or more as the transcript updates
    - Once when the call ends

    We only trigger the agent chain on call.ended —
    that is when we have the full transcript.
    """

    # Get raw payload for signature verification
    payload = await request.body()

    # Verify the request came from Vapi
    signature = request.headers.get("x-vapi-signature", "")
    if not verify_vapi_signature(payload, signature):
        logger.warning("Webhook signature verification failed — rejected request")
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse the event
    try:
        data = json.loads(payload)
        event = VapiWebhookEvent(**data)
    except Exception as e:
        logger.error(f"Failed to parse Vapi webhook payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid payload")

    logger.info(f"Vapi event received: {event.type} | call_sid: {event.call.call_sid}")

    # Route to the right handler based on event type
    if event.type == "call.started":
        await handle_call_started(event)

    elif event.type == "transcript.update":
        await handle_transcript_update(event)

    elif event.type == "call.ended":
        # Trigger the full agent chain in the background
        # We return 200 immediately so Vapi doesn't time out waiting for us
        # The agents run asynchronously after we respond
        background_tasks.add_task(handle_call_ended, event)

    else:
        logger.info(f"Unhandled event type: {event.type} — ignoring")

    # Always return 200 to Vapi immediately
    # If we return anything else Vapi will retry the webhook
    return {"received": True}


# ── Event handlers ────────────────────────────────────────────────────────────

async def handle_call_started(event: VapiWebhookEvent):
    """
    Called when a new call begins.
    We create a call record in Supabase immediately
    so we have a record even if the call drops unexpectedly.
    """
    db = get_db()

    try:
        db.table("calls").insert({
            "call_sid": event.call.call_sid,
            "caller_phone": event.call.caller_phone,
            "status": "in_progress",
            "assistant_id": event.call.assistant_id,
        }).execute()

        logger.info(f"Call started: {event.call.call_sid} from {event.call.caller_phone}")

    except Exception as e:
        # Log but don't crash — the call must continue even if DB write fails
        logger.error(f"Failed to create call record: {e}")


async def handle_transcript_update(event: VapiWebhookEvent):
    """
    Called as the transcript updates during the call.
    We update the transcript in Supabase in real time
    so the dashboard shows live call progress.
    """
    db = get_db()

    try:
        db.table("calls").update({
            "transcript": event.call.transcript,
        }).eq("call_sid", event.call.call_sid).execute()

    except Exception as e:
        logger.error(f"Failed to update transcript: {e}")


async def handle_call_ended(event: VapiWebhookEvent):
    """
    Called when a call ends. This is where the agent chain begins.

    The full transcript is now available.
    We hand it to the planner agent which:
    1. Extracts the 5 intake fields
    2. Determines if all fields are present
    3. Triggers the quote agent if ready
    4. Or tells the voice agent which fields to re-ask

    This runs in the background so we already returned 200 to Vapi.
    If anything fails here — it's logged to state/traces/
    The call record in Supabase is updated with the outcome.
    """
    db = get_db()

    try:
        # Update call status to processing
        db.table("calls").update({
            "status": "processing",
            "transcript": event.call.transcript,
            "duration_seconds": event.call.duration_seconds,
        }).eq("call_sid", event.call.call_sid).execute()

        logger.info(
            f"Call ended: {event.call.call_sid} "
            f"({event.call.duration_seconds}s) — triggering planner"
        )

        # Hand off to the planner agent
        # The planner reads the transcript and extracts the 5 fields
        # From here the chain runs: planner → quote → booking → evaluator
        await run_planner(
            call_sid=event.call.call_sid,
            caller_phone=event.call.caller_phone,
            transcript=event.call.transcript or "",
        )

    except Exception as e:
        logger.error(f"Agent chain failed for call {event.call.call_sid}: {e}")

        # Write failure to traces — never silently discard errors
        try:
            with open(f"state/traces/{event.call.call_sid}-chain-failure.jsonl", "a") as f:
                import json
                f.write(json.dumps({
                    "call_sid": event.call.call_sid,
                    "error": str(e),
                    "stage": "call_ended_handler",
                }) + "\n")
        except Exception as trace_error:
            logger.error(f"Failed to write trace: {trace_error}")

        # Update call status to failed in Supabase
        try:
            db.table("calls").update({
                "status": "failed",
                "error": str(e),
            }).eq("call_sid", event.call.call_sid).execute()
        except Exception:
            pass
