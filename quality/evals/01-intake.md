# Eval 01 — Intake

**Stage:** Planner
**Severity if failed:** BLOCKING — nothing proceeds without all 5 fields
**Checked by:** evaluator.py (automated after every call)

---

## What "done" means for the intake stage

The planner completed its job when ALL of the following are true.
Every box must be checked. No exceptions.

---

## The checklist

**Field completeness:**
- [ ] `name` is present and is not null, empty, or "unknown"
- [ ] `address` is present and contains a street address
- [ ] `issue_type` is present and is exactly one of: `ac` / `heating` / `plumbing`
- [ ] `urgency` is present and is exactly one of: `emergency` / `this_week` / `flexible`
- [ ] `property_type` is present and is exactly one of: `home` / `commercial`

**File integrity:**
- [ ] Plan file exists at `state/artifacts/{call_sid}-plan.json`
- [ ] Plan file parses as valid JSON without errors
- [ ] `next_agent` field is one of: `quote-agent` / `re-ask` / `escalate-to-human`
- [ ] `missing_fields` is an array (empty array is correct when all fields present)
- [ ] `created_at` is a valid ISO 8601 timestamp

---

## Why this is BLOCKING

The quote agent cannot generate a valid quote without all 5 fields.
If `issue_type` is missing — the agent cannot look up a price range.
If `urgency` is missing — the emergency surcharge cannot be applied correctly.
If `address` is missing — a booking cannot be written to the calendar.

A partial intake that proceeds to quoting produces a bad quote.
A bad quote goes to a real customer.
Stop here. Get the fields. Then proceed.

---

## What to do when this eval fails

The planner returns `next_agent: re-ask` with the `missing_fields` array.
The voice agent uses that array to ask for exactly the missing information.
The call continues until all 5 fields are collected or the caller hangs up.

If the caller hangs up before all fields are collected:
- Write the partial record to Supabase with `status: incomplete`
- Do not attempt quote generation
- Flag for manual follow-up on the dashboard
