---
name: hvac-pricing
description: HVAC and plumbing service price ranges for quote generation. Load this skill whenever the quote agent needs to generate a price. Never generate a price from memory — always read from this file.
version: 1.0.0
load_when: quote-agent is generating a quote
---

# HVAC Pricing Skill — Rich Off AI HVAC

**Last updated:** 2026-04-30
**jurisdiction:** United States (adjust ranges for your market)
**Currency:** USD

---

## How to use this file

You are the quote agent.
You have the caller's 5 intake fields.
Your job is to find the matching service category below,
read the base price range, apply any surcharges,
and generate the quote_spoken_text.

You never invent a price.
You never go outside the ranges in this file.
If the issue_type doesn't match any category — escalate to human.
Do not guess.

---

## Base price ranges by service category

### AC (Air Conditioning)

| Service | Price Low | Price High | Notes |
|---------|-----------|------------|-------|
| AC diagnostic / inspection | $75 | $150 | First visit fee |
| Refrigerant recharge (R-410A) | $150 | $400 | Depends on how low |
| AC filter replacement | $50 | $100 | Includes labor |
| AC capacitor replacement | $150 | $300 | Common repair |
| AC contactor replacement | $150 | $300 | Common repair |
| AC coil cleaning | $100 | $250 | Evaporator or condenser |
| AC fan motor replacement | $300 | $600 | Parts + labor |
| AC compressor replacement | $1,200 | $2,500 | Major repair |
| AC unit full replacement | $3,500 | $7,500 | New system installed |
| AC not cooling (unknown cause) | $150 | $500 | Diagnostic + common fix |

### Heating

| Service | Price Low | Price High | Notes |
|---------|-----------|------------|-------|
| Heating diagnostic / inspection | $75 | $150 | First visit fee |
| Furnace filter replacement | $50 | $100 | Includes labor |
| Furnace igniter replacement | $150 | $300 | Common repair |
| Furnace blower motor replacement | $300 | $600 | Parts + labor |
| Heat pump diagnostic | $100 | $200 | |
| Heat pump repair | $200 | $800 | Depends on issue |
| Thermostat replacement | $100 | $300 | Includes programming |
| No heat (unknown cause) | $150 | $600 | Diagnostic + common fix |
| Heating system full replacement | $3,000 | $8,000 | New system installed |

### Plumbing

| Service | Price Low | Price High | Notes |
|---------|-----------|------------|-------|
| Plumbing diagnostic / inspection | $75 | $150 | First visit fee |
| Drain unclogging (minor) | $100 | $250 | Sink, tub, shower |
| Drain unclogging (major) | $200 | $500 | Main line, tree roots |
| Faucet repair or replacement | $150 | $350 | Parts + labor |
| Toilet repair | $100 | $300 | Flapper, fill valve, etc |
| Toilet replacement | $300 | $600 | Parts + labor |
| Pipe leak repair (minor) | $150 | $400 | Single joint or section |
| Pipe leak repair (major) | $400 | $1,500 | Multiple sections |
| Water heater repair | $150 | $500 | Depends on issue |
| Water heater replacement | $800 | $1,800 | Tank style |
| Burst pipe emergency | $400 | $2,000 | Emergency rate applies |
| Water everywhere (unknown cause) | $200 | $1,000 | Emergency rate applies |

---

## Surcharge rules

Apply these AFTER finding the base range.
Apply in this order: emergency first, then commercial.

### Emergency surcharge
**When to apply:** urgency field is `emergency`
**How to apply:** multiply both price_low and price_high by 1.25
**Example:** Base range $150–$400 → Emergency range $188–$500
**Always set:** urgency_surcharge_applied = true

### Commercial surcharge
**When to apply:** property_type field is `commercial`
**How to apply:** multiply both price_low and price_high by 1.20
**Example:** Base range $150–$400 → Commercial range $180–$480
**Always set:** commercial_surcharge_applied = true

### Both surcharges
Apply emergency first. Then apply commercial to the result.
**Example:** Base $150–$400 → Emergency $188–$500 → Commercial $225–$600

---

## Matching issue_type to service category

The caller's issue_type field will be one of: `ac` / `heating` / `plumbing`

Use the caller's description to pick the most specific row in the table.
If the description is vague (e.g. "my AC isn't working") — use the
"unknown cause" row for that category.
Never pick a row from a different category than the issue_type.

**Examples:**
- issue_type: `ac`, caller said "not blowing cold air" → AC not cooling (unknown cause)
- issue_type: `plumbing`, caller said "pipe burst" → Burst pipe emergency
- issue_type: `heating`, caller said "no heat" → No heat (unknown cause)
- issue_type: `plumbing`, caller said "sink is slow" → Drain unclogging (minor)

---

## Quote spoken text format

Always speak the quote as a range. Never a single number.
Always reference what the caller described.
Always end with an invitation to book.

**Standard tone template:**
"Based on what you've described — [brief description of issue] —
a typical [service name] runs between $[low] and $[high].
That can vary depending on what we find when we get there.
Would you like to get that scheduled?"

**Emergency tone template:**
"For [brief description of issue], we're typically looking at
$[low] to $[high] to get that resolved.
Let's get a technician out to you.
What time works best?"

**Rules for quote_spoken_text:**
- No exclamation marks in emergency tone
- No filler words like "Absolutely!" or "Great news!" in emergency tone
- Always include the price range as spoken dollars ("one fifty to three hundred" OR "$150 to $300" — both acceptable)
- Never say "it will definitely be" or "guaranteed" — always "typically" or "usually"
- Maximum 3 sentences

---

## When to escalate to human

Do not attempt to generate a quote if:
- The issue_type does not match ac, heating, or plumbing
- The caller described something that sounds like a gas leak
- The caller described something that sounds like an electrical hazard
- The caller's description doesn't match any row in the tables above

In these cases: set next_agent = escalate-to-human in the plan file.
Do not attempt a quote. Do not guess a price.

---

## Assumption log

**Assumption:** These price ranges are accurate for the US market as of 2026.
**Review date:** 2026-10-30
**Expiry test:** Compare against 3 industry pricing surveys. Adjust any range that has drifted more than 15%.
**Kill threshold:** If advisors consistently override quotes in a specific category — that category's range needs adjustment.
