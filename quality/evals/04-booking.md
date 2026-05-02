# Eval 04 — Booking

**Stage:** Booking Agent
**Severity if failed:** CRITICAL — a booking that cannot be verified is a data integrity failure
**Checked by:** evaluator.py — queries Supabase and Google Calendar directly

---

## What "done" means for the booking stage

The booking agent completed its job when ALL of the following are true.
The evaluator verifies these by querying the actual systems — not by reading the booking agent's self-report.

---

## The checklist

**Calendar:**
- [ ] `calendar_event_id` is a non-empty string in the booking artifact
- [ ] Event actually exists in Google Calendar when queried directly
- [ ] Calendar event contains: customer name, service address, issue type
- [ ] Calendar event has a valid start and end time
- [ ] Calendar event was written BEFORE the Supabase job record

**CRM (Supabase or GHL):**
- [ ] `supabase_job_id` is a valid UUID format (or GHL opportunity ID if GHL adapter)
- [ ] Job record actually exists in the database when queried directly
- [ ] Job record contains: call_sid, customer_name, address, issue_type, quote_low, quote_high
- [ ] Job record `status` is `booked`

**Booking artifact:**
- [ ] Booking file exists at `state/artifacts/{call_sid}-booking.json`
- [ ] All required fields are present (see harness/contracts/booking.json)
- [ ] `booked_at` timestamp is present and valid
- [ ] `crm_destination` matches the `CRM_DESTINATION` env var
- [ ] `calendar_destination` matches the `CALENDAR_DESTINATION` env var

---

## Why this is CRITICAL and not just BLOCKING

BLOCKING means: stop here, the next stage cannot run.
CRITICAL means: stop everything, a human must look at this now.

The difference is the consequence.

A booking that may or may not exist means:
- A technician might show up with no record of the job
- A customer might not get a callback
- A double-booking might occur if the job is re-entered manually
- The business loses trust and potentially loses the customer

Automated recovery makes this worse, not better.
If the system tries to re-book an uncertain booking — it might create a duplicate.
A human looks at every CRITICAL failure. Every time. No exceptions.

---

## What to do when this eval fails

**If calendar_event_id is missing:**
The booking agent halted before completing (Level 3 failure in booking_handler.py).
Check `state/decisions/{call_sid}-data-integrity-calendar_write.json` for full context.
Manually create the calendar event.
Call the customer to confirm their appointment.

**If job record not found in Supabase:**
Calendar write succeeded, CRM write failed.
The technician has a calendar record but operations has no job record.
Manually enter the job in Supabase or GHL.
The booking artifact file has all the data needed.

**In both cases:**
Mark the call `status: manually_resolved` in Supabase after fixing.
Add an entry to `state/decisions/` explaining what happened and what you did.
