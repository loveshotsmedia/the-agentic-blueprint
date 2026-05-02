"""
PLANNER AGENT

Job: Read the call transcript. Extract the 5 intake fields.
     Write a plan to state/artifacts/. Trigger the next agent.

Contract: harness/contracts/planner.json
Trust tier: 3 — WRITE INTERNAL (Supabase only, no external services)

WHAT THIS AGENT DOES:
- Reads the transcript from the Vapi webhook
- Uses Claude Sonnet to extract the 5 required fields
- Writes a plan file to state/artifacts/{call_sid}-plan.json
- If all 5 fields present: triggers the quote agent
- If any fields missing: returns which fields need to be re-asked
- If safety concern detected: escalates to human immediately

WHAT THIS AGENT NEVER DOES:
- Never generates a quote
- Never writes to Google Calendar
- Never sends an SMS
- Never proceeds if the output file has missing required fields
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

# The only model this agent uses — from the contract
MODEL = "claude-sonnet-4-6"

# Budget ceiling from harness/contracts/planner.json
MAX_TOKENS_OUT = 1000


async def run_planner(
    call_sid: str,
    caller_phone: str,
    transcript: str,
) -> dict:
    """
    Main entry point. Called by the Vapi webhook when a call ends.

    Returns the plan dict so the caller can check the outcome.
    Always writes the plan to state/artifacts/ regardless of outcome.
    """
    logger.info(f"Planner starting for call: {call_sid}")

    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # ── Extract the 5 fields from the transcript ────────────────────────────
    extraction_prompt = f"""
You are the intake planner for Rich Off AI HVAC.

A customer just called. Here is the full transcript of the call:

<transcript>
{transcript}
</transcript>

Your job is to extract exactly these 5 fields from the transcript.
Return ONLY a JSON object. No explanation. No markdown. Just the JSON.

{{
  "name": "customer full name or null if not mentioned",
  "address": "service address or null if not mentioned",
  "issue_type": "one of: ac | heating | plumbing | null if unclear",
  "urgency": "one of: emergency | this_week | flexible | null if not mentioned",
  "property_type": "one of: home | commercial | null if not mentioned",
  "emergency_detected": true or false,
  "safety_concern_detected": true or false,
  "notes": "any other relevant context from the call — keep it brief"
}}

Rules:
- Only return null for a field if the customer genuinely did not provide it
- emergency_detected is true if the customer used words like: emergency, flooding,
  burst, no heat, no cooling, gas leak, not working at all, pipe broke, water everywhere
- safety_concern_detected is true if there is any mention of gas leaks, electrical
  sparking, smoke, or anything that could be a safety hazard
- Do not infer or guess values — only extract what was explicitly said
"""

    try:
        response = await client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS_OUT,
            messages=[{"role": "user", "content": extraction_prompt}],
        )

        raw = response.content[0].text.strip()

        # Remove markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        extracted = json.loads(raw)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction response for {call_sid}: {e}")
        return await _write_failure_plan(call_sid, caller_phone, "json_parse_error", str(e))

    except Exception as e:
        logger.error(f"Extraction failed for {call_sid}: {e}")
        return await _write_failure_plan(call_sid, caller_phone, "extraction_error", str(e))

    # ── Safety check — highest priority ────────────────────────────────────
    if extracted.get("safety_concern_detected"):
        logger.warning(f"Safety concern detected on call {call_sid} — escalating to human")
        return await _write_plan(
            call_sid=call_sid,
            caller_phone=caller_phone,
            extracted=extracted,
            next_agent="escalate-to-human",
            reason="Safety concern detected in transcript",
        )

    # ── Check which fields are missing ─────────────────────────────────────
    required_fields = ["name", "address", "issue_type", "urgency", "property_type"]
    missing_fields = [f for f in required_fields if not extracted.get(f)]

    if missing_fields:
        logger.info(f"Call {call_sid} missing fields: {missing_fields} — requesting re-ask")
        return await _write_plan(
            call_sid=call_sid,
            caller_phone=caller_phone,
            extracted=extracted,
            next_agent="re-ask",
            missing_fields=missing_fields,
        )

    # ── All 5 fields present — trigger quote agent ──────────────────────────
    logger.info(f"All 5 fields collected for {call_sid} — triggering quote agent")

    plan = await _write_plan(
        call_sid=call_sid,
        caller_phone=caller_phone,
        extracted=extracted,
        next_agent="quote-agent",
    )

    # Trigger the quote agent
    from src.agents.quote_generator import run_quote_agent
    await run_quote_agent(call_sid=call_sid)

    return plan


async def _write_plan(
    call_sid: str,
    caller_phone: str,
    extracted: dict,
    next_agent: str,
    missing_fields: list = None,
    reason: str = None,
) -> dict:
    """
    Writes the plan file to state/artifacts/.
    This is the handoff document — every subsequent agent reads from here.
    """
    plan = {
        "call_sid": call_sid,
        "caller_phone": caller_phone,
        "stage_1_intake_complete": next_agent == "quote-agent",
        "stage_2_quote_ready": False,
        "stage_3_booking_ready": False,
        "name": extracted.get("name"),
        "address": extracted.get("address"),
        "issue_type": extracted.get("issue_type"),
        "urgency": extracted.get("urgency"),
        "property_type": extracted.get("property_type"),
        "emergency_detected": extracted.get("emergency_detected", False),
        "missing_fields": missing_fields or [],
        "next_agent": next_agent,
        "reason": reason,
        "notes": extracted.get("notes"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Ensure the artifacts directory exists
    Path("state/artifacts").mkdir(parents=True, exist_ok=True)

    plan_path = f"state/artifacts/{call_sid}-plan.json"
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=2)

    logger.info(f"Plan written to {plan_path} | next_agent: {next_agent}")
    return plan


async def _write_failure_plan(
    call_sid: str,
    caller_phone: str,
    error_type: str,
    error_detail: str,
) -> dict:
    """
    Called when the planner itself fails.
    Writes a failure record so nothing is silently lost.
    """
    Path("state/traces").mkdir(parents=True, exist_ok=True)

    trace = {
        "call_sid": call_sid,
        "error_type": error_type,
        "error_detail": error_detail,
        "stage": "planner",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(f"state/traces/{call_sid}-planner-failure.jsonl", "a") as f:
        f.write(json.dumps(trace) + "\n")

    logger.error(f"Planner failure trace written for {call_sid}")
    return {"call_sid": call_sid, "next_agent": "escalate-to-human", "error": error_type}
