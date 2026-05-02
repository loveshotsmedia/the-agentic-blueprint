# Eval 02 — Quote

**Stage:** Quote Agent
**Severity if failed:** BLOCKING — do not book a job with a bad quote
**Checked by:** evaluator.py (automated after every call)

---

## What "done" means for the quote stage

The quote agent completed its job when ALL of the following are true.

---

## The checklist

**Price validity:**
- [ ] `price_low` is a number greater than zero
- [ ] `price_high` is a number greater than zero
- [ ] `price_low` is strictly less than `price_high`
- [ ] `within_skill_range` is `true`
- [ ] Both prices match a row in `harness/skills/hvac-pricing/SKILL.md`

**Surcharges:**
- [ ] If `urgency` is `emergency` — `urgency_surcharge_applied` is `true`
- [ ] If `property_type` is `commercial` — `commercial_surcharge_applied` is `true`
- [ ] If both apply — emergency surcharge was applied first, then commercial

**Spoken text:**
- [ ] `quote_spoken_text` is present
- [ ] `quote_spoken_text` is at least 20 characters
- [ ] `quote_spoken_text` is a complete sentence (not truncated)
- [ ] `quote_spoken_text` contains no placeholder text (`[NAME]`, `[PRICE]`, etc.)
- [ ] `quote_spoken_text` contains the price range
- [ ] `quote_spoken_text` ends with an invitation to book

**File integrity:**
- [ ] Quote file exists at `state/artifacts/{call_sid}-quote.json`
- [ ] Quote file parses as valid JSON
- [ ] `created_at` is a valid ISO 8601 timestamp

---

## Why this is BLOCKING

A wrong price goes to a real customer on a live phone call.
If the agent quotes $5,000 for a $200 drain unclog —
the customer either laughs and hangs up, or you lose money on the job.
Both outcomes are bad.

The pricing skill exists precisely to prevent this.
The evaluator exists to catch it when the skill fails.

---

## What to do when this eval fails

The quote agent regenerates once automatically.
If it fails twice — `status: quality_review_required` is set.
The booking does not proceed.
The dashboard flags the call for manual quote generation.

Do not ship a quote that failed this eval to a customer.
