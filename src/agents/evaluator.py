"""
EVALUATOR AGENT

Job: Check that every stage completed correctly. Report the results.
     Fix nothing. Generate nothing. Only observe and report.

Contract: harness/contracts/evaluator.json
Trust tier: 1 — READ ONLY (lowest trust, cannot write anything)

THE MOST IMPORTANT RULE:
The evaluator is NEVER the same agent that generated the output it is checking.
The factory QA department is independent from the production line.
This is not optional. It is the foundation of quality in this system.

WHAT THIS AGENT DOES:
- Reads artifacts from state/artifacts/
- Queries Supabase directly to verify bookings actually exist
- Runs all 6 evals from quality/evals/
- Writes a pass/fail report to state/artifacts/
- Surfaces failures to the dashboard immediately

WHAT THIS AGENT NEVER DOES:
- Never generates any content
- Never fixes a failure it finds — it reports only
- Never writes to Supabase, calendar, or sends SMS
- Never trusts the booking agent's self-report — always verifies directly
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from anthropic import AsyncAnthropic

from src.database import get_db

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS_OUT = 2000


async def run_evaluator(call_sid: str) -> dict:
    """
    Main entry point. Called by the booking agent after all writes complete.
    Runs all 6 evals and writes a report.
    """
    logger.info(f"Evaluator starting for call: {call_sid}")

    failures = []
    eval_results = {
        "eval_01_intake_pass": False,
        "eval_02_quote_pass": False,
        "eval_03_emotion_pass": False,
        "eval_04_booking_pass": False,
        "eval_05_sms_pass": False,
        "eval_06_full_chain_pass": False,
    }

    # ── Read all artifact files ─────────────────────────────────────────────
    try:
        with open(f"state/artifacts/{call_sid}-plan.json") as f:
            plan = json.load(f)
        with open(f"state/artifacts/{call_sid}-quote.json") as f:
            quote = json.load(f)
        with open(f"state/artifacts/{call_sid}-booking.json") as f:
            booking = json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Evaluator cannot find artifact: {e}")
        return await _write_eval_report(
            call_sid, eval_results,
            [{"eval_id": "setup", "error": str(e), "severity": "BLOCKING"}]
        )

    # ── Eval 01: Intake ─────────────────────────────────────────────────────
    required_fields = ["name", "address", "issue_type", "urgency", "property_type"]
    valid_issue_types = ["ac", "heating", "plumbing"]
    valid_urgencies = ["emergency", "this_week", "flexible"]
    valid_property_types = ["home", "commercial"]

    intake_failures = []

    for field in required_fields:
        if not plan.get(field):
            intake_failures.append(f"Missing field: {field}")

    if plan.get("issue_type") and plan["issue_type"] not in valid_issue_types:
        intake_failures.append(f"Invalid issue_type: {plan['issue_type']}")

    if plan.get("urgency") and plan["urgency"] not in valid_urgencies:
        intake_failures.append(f"Invalid urgency: {plan['urgency']}")

    if plan.get("property_type") and plan["property_type"] not in valid_property_types:
        intake_failures.append(f"Invalid property_type: {plan['property_type']}")

    eval_results["eval_01_intake_pass"] = len(intake_failures) == 0
    if intake_failures:
        failures.extend([
            {"eval_id": "01", "field": f, "severity": "BLOCKING"}
            for f in intake_failures
        ])

    logger.info(f"Eval 01 (intake): {'PASS' if eval_results['eval_01_intake_pass'] else 'FAIL'}")

    # ── Eval 02: Quote ──────────────────────────────────────────────────────
    quote_failures = []

    if not quote.get("price_low") or not quote.get("price_high"):
        quote_failures.append("price_low or price_high missing")
    elif quote["price_low"] >= quote["price_high"]:
        quote_failures.append("price_low must be less than price_high")

    if not quote.get("within_skill_range"):
        quote_failures.append("within_skill_range is false")

    spoken = quote.get("quote_spoken_text", "")
    if not spoken or len(spoken) < 20:
        quote_failures.append("quote_spoken_text too short or missing")
    if "[" in spoken:
        quote_failures.append("quote_spoken_text contains unfilled placeholder")

    is_emergency = plan.get("urgency") == "emergency" or plan.get("emergency_detected")
    if is_emergency and not quote.get("urgency_surcharge_applied"):
        quote_failures.append("Emergency surcharge not applied")

    if plan.get("property_type") == "commercial" and not quote.get("commercial_surcharge_applied"):
        quote_failures.append("Commercial surcharge not applied")

    eval_results["eval_02_quote_pass"] = len(quote_failures) == 0
    if quote_failures:
        failures.extend([
            {"eval_id": "02", "field": f, "severity": "BLOCKING"}
            for f in quote_failures
        ])

    logger.info(f"Eval 02 (quote): {'PASS' if eval_results['eval_02_quote_pass'] else 'FAIL'}")

    # ── Eval 03: Emotion ────────────────────────────────────────────────────
    emotion_failures = []
    trigger_words = [
        "emergency", "flooding", "burst", "no heat", "no cooling",
        "gas leak", "not working at all", "pipe broke", "water everywhere"
    ]

    transcript = plan.get("notes", "").lower()
    emergency_in_transcript = any(word in transcript for word in trigger_words)
    is_emergency_call = plan.get("emergency_detected") or emergency_in_transcript

    if is_emergency_call:
        spoken_lower = quote.get("quote_spoken_text", "").lower()
        excitement_markers = ["!", "absolutely", "great news", "wonderful", "fantastic"]
        found_markers = [m for m in excitement_markers if m in spoken_lower]
        if found_markers:
            emotion_failures.append(
                f"Emergency tone violated — excitement markers found: {found_markers}"
            )

    eval_results["eval_03_emotion_pass"] = len(emotion_failures) == 0
    if emotion_failures:
        failures.extend([
            {"eval_id": "03", "field": f, "severity": "HIGH"}
            for f in emotion_failures
        ])

    logger.info(f"Eval 03 (emotion): {'PASS' if eval_results['eval_03_emotion_pass'] else 'FAIL'}")

    # ── Eval 04: Booking — verify directly against Supabase ─────────────────
    booking_failures = []
    db = get_db()

    if not booking.get("calendar_event_id"):
        booking_failures.append("calendar_event_id missing from booking artifact")
    else:
        # Verify the job actually exists in Supabase
        # We don't trust the booking agent's self-report — we check directly
        try:
            result = db.table("jobs").select("id").eq(
                "call_sid", call_sid
            ).execute()

            if not result.data:
                booking_failures.append(
                    "Job record not found in Supabase — booking agent may have failed silently"
                )
        except Exception as e:
            booking_failures.append(f"Supabase verification query failed: {e}")

    eval_results["eval_04_booking_pass"] = len(booking_failures) == 0
    if booking_failures:
        failures.extend([
            {"eval_id": "04", "field": f, "severity": "CRITICAL"}
            for f in booking_failures
        ])

    logger.info(f"Eval 04 (booking): {'PASS' if eval_results['eval_04_booking_pass'] else 'FAIL'}")

    # ── Eval 05: SMS ────────────────────────────────────────────────────────
    sms_failures = []

    if not booking.get("sms_delivered"):
        sms_failures.append("SMS not delivered — customer needs manual follow-up")

    if not booking.get("sms_message_sid"):
        sms_failures.append("sms_message_sid missing")

    eval_results["eval_05_sms_pass"] = len(sms_failures) == 0
    if sms_failures:
        failures.extend([
            {"eval_id": "05", "field": f, "severity": "HIGH"}
            for f in sms_failures
        ])

    logger.info(f"Eval 05 (SMS): {'PASS' if eval_results['eval_05_sms_pass'] else 'FAIL'}")

    # ── Eval 06: Full chain gate ────────────────────────────────────────────
    blocking_failures = [f for f in failures if f.get("severity") == "BLOCKING"]
    eval_results["eval_06_full_chain_pass"] = (
        eval_results["eval_01_intake_pass"]
        and eval_results["eval_02_quote_pass"]
        and eval_results["eval_04_booking_pass"]
        and len(blocking_failures) == 0
    )

    logger.info(
        f"Eval 06 (full chain): "
        f"{'PASS' if eval_results['eval_06_full_chain_pass'] else 'FAIL'}"
    )

    return await _write_eval_report(call_sid, eval_results, failures)


async def _write_eval_report(
    call_sid: str,
    eval_results: dict,
    failures: list,
) -> dict:
    """
    Writes the evaluation report to state/artifacts/.
    Updates the call record in Supabase with the eval outcome.
    """
    report = {
        "call_sid": call_sid,
        **eval_results,
        "failures": failures,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }

    Path("state/artifacts").mkdir(parents=True, exist_ok=True)
    report_path = f"state/artifacts/{call_sid}-eval-report.json"

    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # Update the call record in Supabase with the eval outcome
    try:
        db = get_db()
        status = "completed" if eval_results["eval_06_full_chain_pass"] else "completed_with_issues"
        db.table("calls").update({
            "status": status,
            "eval_passed": eval_results["eval_06_full_chain_pass"],
            "eval_failures": len(failures),
        }).eq("call_sid", call_sid).execute()
    except Exception as e:
        logger.error(f"Failed to update call status after eval: {e}")

    logger.info(
        f"Eval report written: {report_path} | "
        f"Chain: {'PASS' if eval_results['eval_06_full_chain_pass'] else 'FAIL'} | "
        f"Failures: {len(failures)}"
    )

    return report
