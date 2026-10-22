# AGENTS.md — The Agentic Blueprint

> **How to use this file:**
> Copy everything below the line and paste it into Claude Code
> before starting any work on this system.
> This is your programming interface — not a README, not docs.
> This is the instruction set for your AI workforce.

---

## What this system is

**Business:** Rich Off AI HVAC (replace with your business name)
**What it does:** Answers inbound calls, generates quotes, books jobs
**Stack:** Vapi (voice) → FastAPI on Railway → Supabase + Google Calendar
**Demo line:** +1 (239) 294-2140

This is a **sequential agentic system** — meaning the agents work in order, one after another, like an assembly line. Each agent does exactly one job and hands off to the next. No agent does more than one job.

```
Inbound call
     ↓
[PLANNER]       — reads the brief, breaks the call into stages
     ↓
[QUOTE AGENT]   — generates a quote from what the caller said
     ↓
[BOOKING AGENT] — writes to calendar, sends SMS confirmation
     ↓
[EVALUATOR]     — checks that every stage completed correctly
```

---

## The three types of folders

Before touching any file, understand this. Everything in this repo is one of three things:

**You write it — agents only read it.**
`.claude/agents/`, `harness/`, `quality/evals/`, `AGENTS.md`, `vision.md`
These files define the rules. Never auto-generate them. Never let an agent modify them.

**Agents use it — built by you and agents together.**
`src/`, `quality/tests/`, `quality/playwright/`
This is the working code. Agents can write and edit these files.

**System fills it — never edit manually.**
`state/traces/`, `state/decisions/`, `state/artifacts/`
These fill up as the system runs. Treat them as read-only logs.

If you are ever unsure which category a file belongs to — stop and check this list before proceeding.

---

## The workforce (.claude/agents/)

There are exactly 4 agents in this system. Do not add more without a specific measured reason.

### planner.md
**Job:** Read the inbound call brief. Break it into stages. Write a plan.
**Does NOT do:** Execute anything. Generate any content.
**Model:** claude-sonnet-4-6
**Trust tier:** HIGH — operates on call metadata only, no external writes
**Allowed tools:** read_file, supabase_query (read-only)
**Forbidden tools:** supabase_write, calendar_write, sms_send, shell_exec

### quote-agent.md
**Job:** Take the 5 fields from the call intake. Generate a quote in range for the service type.
**Does NOT do:** Book anything. Contact the customer. Write to any database.
**Model:** claude-haiku-4-5-20251001
**Trust tier:** MEDIUM — generates content, no external side effects
**Allowed tools:** read_file (HVAC pricing skill only)
**Forbidden tools:** everything else
**Critical rule:** Quote must be within the range defined in `harness/skills/hvac-pricing/SKILL.md`. Any quote outside range fails the eval and must regenerate. Never hallucinate a price.

### booking-agent.md
**Job:** Write the confirmed booking to Google Calendar and Supabase. Send SMS confirmation.
**Does NOT do:** Generate quotes. Modify existing bookings without explicit instruction.
**Model:** claude-sonnet-4-6
**Trust tier:** HIGH — has external write permissions
**Allowed tools:** calendar_write, supabase_write, sms_send
**Forbidden tools:** shell_exec, file_write (outside state/artifacts/)
**Critical rule:** Always write to calendar BEFORE writing to Supabase. If calendar write fails, do not write to Supabase and do not send SMS. Log the failure to state/traces/.

### evaluator.md
**Job:** Check that every stage completed correctly. Runs after the full chain.
**Does NOT do:** Generate anything. Fix anything. It only reports.
**Model:** claude-haiku-4-5-20251001
**Trust tier:** LOW — read-only access to everything
**Allowed tools:** read_file, supabase_query (read-only), calendar_read
**Forbidden tools:** everything with write permissions
**Critical rule:** The evaluator is NEVER the same agent that generated the output it is checking. Separate context. Separate call. This is non-negotiable.

---

## The harness rules (non-negotiable)

These rules apply to every agent in the system. No exceptions.

**Rule 1 — Contracts before prompts.**
No agent gets a system prompt until its contract exists in `harness/contracts/`.
The contract defines inputs, outputs, budget, permissions, and completion condition.

**Rule 2 — State lives on disk.**
Every piece of data that must survive a restart lives in `state/` or Supabase.
Nothing important lives only in a context window.
Test: if you restart Railway right now, does the system resume correctly?

**Rule 3 — Narrow first.**
Start with the minimum approach. Add complexity only when a specific failure trace in `state/traces/` justifies it. Never add tools speculatively.

**Rule 4 — The evaluator is not the generator.**
The agent that produced an output cannot be the agent that checks it.
Always separate contexts. Always.

**Rule 5 — Default deny on tools.**
Every agent starts with zero tool access. Tools are added explicitly per contract.
An agent asking for "just one more tool" gets the same answer every time: cite the failure trace first.

**Rule 6 — One axis per retry.**
When an agent fails, broaden by exactly one thing: add one tool, OR widen context, OR escalate to a stronger model. Never all three at once. You lose attribution if you change everything at once.

**Budget ceilings (system-wide defaults):**
```
max_tokens_in:        50,000
max_tokens_out:       4,000
max_tool_calls:       10
max_wall_clock:       2 minutes
max_cost_per_call:    $0.10
on_breach:            halt_and_log — never silently overrun
```

---

## The adapter pattern

This system routes data to two possible destinations per flow.
**One environment variable controls everything.**

```bash
# In your .env file:
CRM_DESTINATION=supabase     # or: ghl
CALENDAR_DESTINATION=google  # or: ghl_calendar
```

The agent code never changes. The adapter handles the routing.
This is how you swap the entire CRM without rebuilding a single agent.

Think of it like a phone charger: same phone, different power source.
The adapter is the cable. The agent is the phone.

---

## The quality system (quality/)

Three tools. One concept. Different jobs.

**quality/evals/** — Written by you. Defines what "done" means.
These are checklists. Markdown files. You write them before any code runs.
Example: "The quote eval passes if: service type is identified, price is in range, no placeholder values exist."

**quality/tests/** — Python code. Checks the logic automatically.
Unit tests for quote generation. Integration tests for the adapter swap.
Run with: `bash scripts/test.sh`

**quality/playwright/** — A robot that clicks through the dashboard.
Books a job end-to-end via the UI. Confirms it appears in the dashboard.
Confirms it hit Google Calendar. Confirms SMS record exists in Supabase.
Run with: `bash scripts/test.sh --e2e`

**The deploy gate:**
Nothing ships unless `quality/evals/06-full-chain.md` passes.
That eval is the only one that blocks a deploy.
Evals 01-05 are diagnostic — they tell you where something broke.
Eval 06 is the gate — it tells you whether to ship.

---

## The call flow (5 questions)

The voice agent always collects exactly these 5 fields before generating a quote.
If any field is missing, the intake eval fails and the agent re-asks.

```
1. name          — "Can I get your name?"
2. address       — "And what's the address for the job?"
3. issue_type    — "What's the issue — AC, heating, or plumbing?"
4. urgency       — "How urgent is this — emergency, this week, or flexible?"
5. property_type — "Is this a home or a commercial property?"
```

**Emotion detection rule:**
If the caller uses any of these words: "emergency", "flooding", "no heat", "burst", "gas leak", "not working at all" — the agent shifts tone immediately. Bubbly and energetic is the default. Calm and direct is the emergency mode. The eval in `quality/evals/03-emotion.md` checks this on every call.

---

## State paths

Every piece of runtime data has a deterministic path.

```
state/traces/        Raw call traces. Never summarized. Never deleted.
state/decisions/     Why design decisions were made. Append-only.
state/artifacts/     Completed quotes and booking confirmations.
state/assumptions.md Every design choice with an expiry date.
```

**The test for whether state is on disk:**
Wipe the entire context window right now.
Can the system resume from `state/` and Supabase alone?
If yes — state is on disk. If no — something is stored in memory that shouldn't be.

---

## File you should read before writing any code

```
vision.md                           Why this exists. What Rich Off AI HVAC is.
harness/RUNTIME.md                  The full rules and budget ceilings.
harness/contracts/[agent].json      What each agent is accountable for.
harness/skills/hvac-pricing/SKILL.md  The pricing ranges for quote generation.
quality/evals/01-intake.md          What "done" means for the intake stage.
.env.example                        Every variable you need to fill in.
```

---

## What this is NOT

- Not a chatbot. Not a FAQ bot. Not a widget.
- Not a system that requires a human to review every action before it executes.
- Not built for one specific business — swap the business name, the phone number, and the pricing skill and this works for any field service business.

---

## Red flags — stop and ask before proceeding

If you find yourself doing any of these things, stop:

- Adding a new agent without a contract in `harness/contracts/`
- Letting the same agent generate AND evaluate its own output
- Storing booking data only in a context window (write to Supabase immediately)
- Adding a tool to an agent without a failure trace that justifies it
- Writing to the calendar after writing to Supabase (always calendar first)
- Summarizing `state/traces/` — raw traces only, always
- Changing more than one thing when debugging a failure

---

*This file is The Blueprint's programming interface.*
*Paste it into Claude Code. Let it read the contracts. Then build.*
*The framework does the rest.*

<!-- BEGIN test-data-e2e -->
## Prove software with test data, then delete the test data (Cameron, 2026-10-22: every agent, every model, every repo)

Cameron: "whenever we are building software, we are to test it through and through with TEST
data so that we can ensure that the software is functioning properly. We can NEVER know how
someone would use the software in real time but we can create mock data and test accounts to
ensure the functionality of the software is doing what it needs to do. Whenever the tests are
proven and functional and verified end-2-end, we must delete the test data."

1. **We prove readiness; customers do not.** Never make "ready", "launch-ready" or "ready to
   market" depend on a real user, pilot family or client trying it first. Create test accounts
   and realistic mock data, then run every user journey end to end yourself. A readiness verdict
   cites that end-to-end evidence; "no real user has tried it" is never the reason for "not ready".
2. **End to end means the deployed system**: real sign-in with test accounts, real screens, API,
   database, background jobs and outbound channels (sends go to Cameron's test bench:
   sandbox@dartix.ai, +14707753567, cameron@dartix.ai). Cover every role, the happy path, edge
   cases and error paths. Unit tests and local runs alone are not proof.
3. **Tag everything you create** so it can be found and removed: test emails like
   `test+<run-id>@dartix.ai` (or the repo's documented test domain), names starting
   `TEST-<run-id>`, and every created ID written to a run manifest
   (`work/test-data/<run-id>.json` or the handoff STATUS).
4. **Delete it once proven.** After the end-to-end run passes, delete every record, account,
   file, storage object, calendar event, CRM contact and provider object (Twilio, Vapi,
   ElevenLabs, Stripe, Resend and the like) that the run created, in dependency order. Re-query
   to prove zero remain and put that count in the completion report. Delete only what is in the
   manifest; never touch real customer data.
5. **A failed run keeps its test data** until the fix is proven (it is the evidence), then
   deletes it. Test data left behind is an open item under the reporting contract.
6. **Standing test-bench accounts stay** (the sandbox@dartix.ai advisor and any documented demo
   account); the data each run creates inside them is deleted.
7. Creating and deleting your own tagged test data, including in production, is routine work
   under the approval scope and needs no approval. Real-customer data, schema migrations and
   destructive changes to anything outside the manifest keep their existing gates.
<!-- END test-data-e2e -->
