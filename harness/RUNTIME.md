# RUNTIME.md — The Employee Handbook

**System:** Rich Off AI HVAC / The Agentic Blueprint
**Last updated:** 2026-04-30
**Written by:** Cam Wilson
**Applies to:** Every agent in this system. No exceptions.

---

## What this file is

Think of this as the employee handbook for your AI workforce.

When you hire a new employee, you don't explain the rules every single day.
You hand them the handbook on Day 1.
They read it. They follow it. Forever.

This is that handbook.

Every agent in this system — the planner, the quote agent,
the booking agent, the evaluator — operates inside these rules.
The rules never change mid-task.
The agents never negotiate them.
If an agent violates a rule, it halts and reports. It does not proceed.

---

## The three layers every agent knows about

Before anything else, every agent must understand
which layer it operates in.

**Layer 1 — Infrastructure (you manage this)**
Vapi, Railway, Supabase, Google Calendar, Twilio, GoHighLevel.
These are the tools the system connects to.
Agents use them through adapters.
Agents never connect to infrastructure directly.

**Layer 2 — Runtime (this file)**
The universal rules. Budgets. Permissions. Failure handling.
Written by the human. Read by every agent. Never modified by agents.

**Layer 3 — Task-specific (contracts + skills)**
What each individual agent is accountable for.
Lives in `harness/contracts/`.
One contract per agent. One job per agent.

If an agent is ever unsure which layer a decision belongs to —
it belongs to the layer closest to the human.
When in doubt, stop and ask.

---

## Budget ceilings

These are hard limits. Not suggestions. Not defaults.
When any ceiling is hit, the agent halts immediately and logs to `state/traces/`.
It never silently overruns.

```
max_tokens_in:         50,000     per agent call
max_tokens_out:        4,000      per agent call
max_tool_calls:        10         per agent call
max_wall_clock:        2 minutes  per agent call
max_cost_per_call:     $0.10      per agent call
max_cost_per_booking:  $0.30      full chain end-to-end
```

**Why these numbers matter:**
At 20 calls per day, this system costs under $2/day to run.
If any single call exceeds $0.30 something is wrong.
The budget ceiling catches it before it becomes a $200 surprise invoice.

**On breach:**
```
1. Halt immediately
2. Log full trace to state/traces/[timestamp]-breach.jsonl
3. Write to state/decisions/ what was happening when breach occurred
4. Surface error to dashboard
5. Do NOT retry automatically — wait for human review
```

---

## The permission model

**Default deny. Explicit allow.**

Every agent starts with zero permissions.
Tools are added one at a time in the contract.
An agent never has access to a tool that isn't listed in its contract.

Think of it like a keycard system in an office building.
A new employee doesn't get a master key on Day 1.
They get access to exactly the rooms they need for their job.
Nothing more.

**The four permission tiers:**

```
TIER 1 — READ ONLY
Can read files and query Supabase.
Cannot write anything anywhere.
Used by: evaluator

TIER 2 — GENERATE ONLY  
Can read files and call LLM APIs.
Cannot write to any database or external service.
Used by: quote-agent

TIER 3 — WRITE INTERNAL
Can read, generate, and write to Supabase.
Cannot write to external services (calendar, SMS).
Used by: planner

TIER 4 — WRITE EXTERNAL
Can read, generate, write to Supabase,
write to Google Calendar, and send SMS.
Used by: booking-agent only
```

**Why this matters:**
If the quote agent gets compromised or goes rogue —
it cannot book a job, send an SMS, or touch the calendar.
It can only generate text.
The damage is contained to Tier 2.

---

## State rules

**Rule: Everything important lives on disk or in Supabase. Never only in memory.**

The test is simple:
Restart Railway right now.
Can the system resume every in-flight booking from Supabase alone?
If yes — state is correct.
If no — something is stored in memory that should be in the database.

**The four state paths and what lives in each:**

```
state/traces/
  Raw execution traces from every agent call.
  Never summarized. Never deleted.
  Format: JSONL — one event per line.
  Why raw matters: summarizing traces drops diagnostic
  accuracy by 30%. The signal lives in the detail.

state/decisions/
  Why design decisions were made.
  Append-only — never edit existing entries, only add new ones.
  Format: markdown, one file per decision.
  Example: "2026-04-30 — chose sequential pattern over parallel
  because call stages are dependent. Quote requires intake.
  Booking requires quote. Cannot parallelize."

state/artifacts/
  What the agents actually produced.
  Completed quotes. Booking confirmations. SMS logs.
  These are the receipts.

state/assumptions.md
  Every design choice that encodes a limitation.
  Each entry has an expiry date.
  Review quarterly. Kill what expired.
  Example: "Assumed Claude Haiku cannot reliably detect
  emergency keywords without explicit prompt scaffolding.
  Review: 2026-07-30. Test: run 100 calls, measure
  false negative rate on emergency detection."
```

---

## Failure handling

**The three levels of failure:**

**Level 1 — Recoverable**
Agent failed on one attempt.
Broaden by exactly ONE axis and retry.
Log the broadening and the reason to `state/traces/`.

The four broadening axes — use one per retry, never all at once:
```
Axis 1: Add one tool (only if trace shows missing capability)
Axis 2: Widen context (only if trace shows missing information)
Axis 3: Escalate model tier (only if trace shows reasoning failure)
Axis 4: Split into smaller stages (only if trace shows stage too large)
```

**Level 2 — Unrecoverable**
Three attempts failed.
Halt. Log full trace. Surface to dashboard.
Human reviews before any retry.

**Level 3 — Data integrity failure**
Any failure that involves a booking that may or may not
have written to the calendar or Supabase.
Halt everything immediately.
Do not attempt recovery automatically.
Log to `state/decisions/` with full context.
Human resolves manually.

**Why Level 3 is treated differently:**
A double-booked calendar slot or a missing booking
affects a real customer at a real address.
Automated recovery could make it worse.
Human eyes on every data integrity failure. Always.

---

## The call chain order

The agents always execute in this order.
This order never changes.

```
1. PLANNER      reads brief, builds stage plan
2. QUOTE AGENT  generates quote from intake data
3. BOOKING AGENT writes to calendar, writes to Supabase, sends SMS
4. EVALUATOR    checks that 1, 2, and 3 completed correctly
```

**The handoff rule:**
Each agent writes its output to `state/artifacts/` before the next agent starts.
The next agent reads from `state/artifacts/` — not from memory.
No agent passes data to the next agent through a function return or variable.
Disk is the transport layer. Always.

**Why this matters for your viewers:**
If the server restarts between step 2 and step 3 —
step 3 reads from `state/artifacts/` and picks up exactly where it left off.
The booking is not lost.
The customer gets their confirmation.
The owner never knows there was a restart.

---

## The emotion detection rule

This rule applies to the voice agent (Vapi) before the planner runs.

**Default mode: bubbly and energetic**
Warm. Fast. Helpful.
"Thanks for calling Rich Off AI HVAC — I'd love to help you today!"

**Emergency mode: calm and direct**
No excitement. No filler. Slower pace.
"I understand. Let's get someone out to you as quickly as possible."

**Trigger words that switch to emergency mode:**
```
emergency, flooding, burst, no heat, no cooling,
gas leak, not working at all, pipe broke,
water everywhere, sparking, smoke
```

**The rule:**
Detection happens on the FIRST response from the caller.
If any trigger word appears — mode switches immediately.
Mode does not switch back during the same call.
Once emergency mode is active it stays active.

This is checked by `quality/evals/03-emotion.md` on every call.

---

## The adapter rule

**One environment variable controls data destination.**

```bash
CRM_DESTINATION=supabase      # default
CALENDAR_DESTINATION=google   # default
```

Changing these variables reroutes the entire system.
No agent code changes. No contract changes. No redeploy required.
The adapter handles the translation.

**The adapter contract:**
Every adapter must implement the same interface.
`supabase.py` and `ghl.py` expose identical function signatures.
The agent calls `crm.write_booking(data)` — it never knows
whether that goes to Supabase or GoHighLevel.

If an adapter fails — log to `state/traces/` and surface to dashboard.
Never silently fail a data write.

---

## The subtraction rule

**This runs every sprint. Not quarterly. Every sprint.**

Before any new tool, agent, or stage is added — answer these questions:

```
1. Which specific failure trace justifies this addition?
2. What is the simplest possible fix for that failure?
3. Can an existing agent handle this with a prompt change instead?
```

If you cannot answer question 1 with a file path in `state/traces/` —
the addition is not justified.
Do not add it.

Complexity is not free.
Every new agent is a new failure surface.
Every new tool is a new permission to manage.
Every new stage is a new thing that can break at 3am.

The goal is the minimum system that does the job completely.
Not the most impressive system. The most reliable one.

---

## What agents never do

This list applies to every agent in the system.
No contract overrides these.

```
❌ Never modify vision.md, AGENTS.md, or RUNTIME.md
❌ Never write to state/decisions/ without a human prompt
❌ Never retry a data integrity failure automatically
❌ Never add a tool without a contract change
❌ Never summarize state/traces/ — raw only
❌ Never write to Supabase before writing to the calendar
❌ Never proceed if any of the 5 intake fields are missing
❌ Never generate a quote outside the ranges in hvac-pricing/SKILL.md
❌ Never send an SMS before the calendar write is confirmed
```

---

## Sign-off

Before any code runs in this system, confirm:

- [ ] All 4 agent contracts exist in `harness/contracts/`
- [ ] `.env.example` has every required variable
- [ ] `state/` folders exist with `.gitkeep` files
- [ ] `quality/evals/01-intake.md` through `06-full-chain.md` are written
- [ ] Railway is connected to the GitHub repo
- [ ] The Twilio number is uploaded to Vapi

If any box is unchecked — do not deploy.
Fix it first. Then deploy.

---

*This file is read-only for agents.*
*If you are an AI agent reading this — follow every rule in it.*
*Do not modify it. Do not negotiate it. Do not work around it.*
