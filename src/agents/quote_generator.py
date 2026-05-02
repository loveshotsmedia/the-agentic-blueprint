"""
QUOTE AGENT

Job: Read the plan file. Look up the price range. Generate a quote.
     Write the quote to state/artifacts/. Trigger the booking agent.

Contract: harness/contracts/quote.json
Trust tier: 2 — GENERATE ONLY (no database writes, no external services)

WHAT THIS AGENT DOES:
- Reads the plan file from state/artifacts/
- Reads the HVAC pricing ranges from harness/skills/hvac-pricing/SKILL.md
- Uses Claude Haiku to generate a quote within the correct range
- Applies emergency and commercial surcharges when applicable
- Writes the quote to state/artifacts/{call_sid}-quote.json
- Triggers the booking agent

WHAT THIS AGENT NEVER DOES:
- Never writes to Supabase
- Never touches the calendar
- Never sends an SMS
- Never invents a price not in the SKILL.md pricing table
- Never quotes a single fixed price — always a range
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from anthropic import AsyncAnthropic

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS_OUT = 500

# Path to the pricing skill — the only file this agent reads
PRICING_SKILL_PATH = "harness/skills/hvac-pricing/SKILL.md"


async def run_quote_agent(call_sid: str) -> dict:
    """
    Main entry point. Called by the planner when all 5 fields are collected.
    """
    logger.info(f"Quote agent starting for call: {call_sid}")

    # ── Read the plan file ──────────────────────────────────────────────────
    plan_path = f"state/artifacts/{call_sid}-plan.json"

    try:
        with open(plan_path) as f:
            plan = json.load(f)
    except FileNotFoundError:
        logger.error(f"Plan file not found: {plan_path}")
        return await _write_failure_quote(call_sid, "plan_file_not_found")

    # ── Verify all 5 fields are present ────────────────────────────────────
    required = ["name", "address", "issue_type", "urgency", "property_type"]
    missing = [f for f in required if not plan.get(f)]

    if missing:
        logger.error(f"Plan missing required fields for {call_sid}: {missing}")
        return await _write_failure_quote(call_sid, f"missing_fields: {missing}")

    # ── Read the pricing skill ──────────────────────────────────────────────
    try:
        with open(PRICING_SKILL_PATH) as f:
            pricing_skill = f.read()
    except FileNotFoundError:
        logger.error(f"Pricing skill not found at {PRICING_SKILL_PATH}")
        return await _write_failure_quote(call_sid, "pricing_skill_not_found")

    # ── Generate the quote ──────────────────────────────────────────────────
    client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    is_emergency = plan.get("urgency") == "emergency" or plan.get("emergency_detected")
    is_commercial = plan.get("property_type") == "commercial"
    tone = "emergency" if is_emergency else "standard"

    quote_prompt = f"""
You are the quote agent for Rich Off AI HVAC.

A customer called with this information:
- Name: {plan['name']}
- Address: {plan['address']}
- Issue type: {plan['issue_type']}
- Urgency: {plan['urgency']}
- Property type: {plan['property_type']}
- Emergency detected: {is_emergency}
- Notes: {plan.get('notes', 'none')}

Here are the approved pricing ranges you must use:

<pricing>
{pricing_skill}
</pricing>

Generate a quote following ALL rules in the pricing skill above.
Return ONLY a JSON object. No explanation. No markdown. Just JSON.

{{
  "service_category": "the specific row from the pricing table you matched",
  "price_low": 150,
  "price_high": 400,
  "currency": "USD",
  "urgency_surcharge_applied": true or false,
  "commercial_surcharge_applied": true or false,
  "within_skill_range": true,
  "quote_spoken_text": "The exact sentence the voice agent speaks to the customer",
  "tone": "{tone}"
}}

Rules:
- price_low must be less than price_high
- within_skill_range must be true — if you cannot match to a pricing row, set
  service_category to "no_match" and within_skill_range to false
- quote_spoken_text must follow the {tone} tone template in the pricing skill
- Apply surcharges exactly as defined in the pricing skill
- Never invent a price outside the ranges in the pricing table
"""

    for attempt in range(3):
        try:
            response = await client.messages.create(
                model=MODEL,
                max_tokens=MAX_TOKENS_OUT,
                messages=[{"role": "user", "content": quote_prompt}],
            )

            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]

            quote_data = json.loads(raw)

            # ── Validate the quote ──────────────────────────────────────────
            validation_errors = _validate_quote(quote_data)

            if validation_errors:
                logger.warning(
                    f"Quote validation failed on attempt {attempt + 1} "
                    f"for {call_sid}: {validation_errors}"
                )
                if attempt == 2:
                    return await _write_failure_quote(
                        call_sid,
                        f"validation_failed_after_3_attempts: {validation_errors}"
                    )
                continue

            # ── Write the quote file ────────────────────────────────────────
            quote = {
                "call_sid": call_sid,
                **quote_data,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            Path("state/artifacts").mkdir(parents=True, exist_ok=True)
            quote_path = f"state/artifacts/{call_sid}-quote.json"

            with open(quote_path, "w") as f:
                json.dump(quote, f, indent=2)

            logger.info(
                f"Quote written for {call_sid}: "
                f"${quote_data['price_low']}–${quote_data['price_high']} "
                f"({quote_data['service_category']})"
            )

            # ── Update plan file to mark stage 2 complete ───────────────────
            plan["stage_2_quote_ready"] = True
            with open(plan_path, "w") as f:
                json.dump(plan, f, indent=2)

            # ── Trigger booking agent ───────────────────────────────────────
            from src.agents.booking_handler import run_booking_agent
            await run_booking_agent(call_sid=call_sid)

            return quote

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                return await _write_failure_quote(call_sid, f"json_parse_error: {e}")

        except Exception as e:
            logger.error(f"Quote generation error on attempt {attempt + 1}: {e}")
            if attempt == 2:
                return await _write_failure_quote(call_sid, f"generation_error: {e}")


def _validate_quote(quote_data: dict) -> list:
    """
    Validates a generated quote against the rules in harness/contracts/quote.json.
    Returns a list of validation errors. Empty list means the quote is valid.
    """
    errors = []

    if not quote_data.get("price_low"):
        errors.append("price_low is missing")
    if not quote_data.get("price_high"):
        errors.append("price_high is missing")
    if quote_data.get("price_low", 0) >= quote_data.get("price_high", 0):
        errors.append("price_low must be less than price_high")
    if not quote_data.get("within_skill_range"):
        errors.append("within_skill_range is false — price outside approved ranges")
    if not quote_data.get("quote_spoken_text"):
        errors.append("quote_spoken_text is missing")
    if len(quote_data.get("quote_spoken_text", "")) < 20:
        errors.append("quote_spoken_text is too short to be a complete sentence")
    if "[" in quote_data.get("quote_spoken_text", ""):
        errors.append("quote_spoken_text contains unfilled placeholder")

    return errors


async def _write_failure_quote(call_sid: str, reason: str) -> dict:
    """
    Called when the quote agent fails.
    Writes a trace. Never silently discards errors.
    """
    Path("state/traces").mkdir(parents=True, exist_ok=True)

    trace = {
        "call_sid": call_sid,
        "error": reason,
        "stage": "quote_agent",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with open(f"state/traces/{call_sid}-quote-failure.jsonl", "a") as f:
        f.write(json.dumps(trace) + "\n")

    logger.error(f"Quote failure trace written for {call_sid}: {reason}")
    return {"call_sid": call_sid, "error": reason, "next_agent": "escalate-to-human"}
