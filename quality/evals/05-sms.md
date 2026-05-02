# Eval 05 — SMS Confirmation

**Stage:** Booking Agent (final step)
**Severity if failed:** HIGH — customer did not receive confirmation, requires manual follow-up
**Checked by:** evaluator.py (automated after every call)

---

## What "done" means for the SMS stage

The customer received a text message confirming their booking
before the call processing chain completed.

---

## The checklist

**Delivery:**
- [ ] `sms_delivered` is `true` in the booking artifact
- [ ] `sms_message_sid` is a non-empty string (Twilio message ID)
- [ ] SMS log record exists in Supabase `sms_log` table

**Content:**
- [ ] SMS was sent to the original `caller_phone` — not any other number
- [ ] SMS contains the customer's first name
- [ ] SMS contains the job date and time
- [ ] SMS contains the service address
- [ ] SMS contains the business callback number
- [ ] SMS is under 320 characters (2 message segments maximum)
- [ ] SMS contains no placeholder text

---

## Why this matters

The confirmation text is the customer's proof that their booking is real.

Without it:
- They don't know if the AI actually booked them
- They might call back and book again (duplicate)
- They might not show up (or be home) for the technician
- They might leave a negative review about uncertainty

It takes 10 seconds to send a text.
The system sends it automatically every time.
This eval confirms it happened.

---

## What to do when this eval fails

The booking still exists — calendar and CRM writes succeeded.
The customer just didn't get their confirmation text.

**Immediate action:**
Send a manual text or call the customer from the business number.
Use the booking artifact at `state/artifacts/{call_sid}-booking.json`
for the customer name, phone, and job details.

**Investigation:**
Check Twilio logs for the `sms_message_sid`.
Common causes: invalid phone number format, Twilio credentials issue,
phone number not A2P registered for business messaging.

**After resolving:**
Update `sms_delivered` to `true` in the Supabase jobs table.
Log the resolution to `state/decisions/`.
