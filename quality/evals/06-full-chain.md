# Eval 06 — Full Chain (The Deploy Gate)

**Stage:** End-to-end
**Severity if failed:** DEPLOY GATE — nothing ships until this passes
**Checked by:** evaluator.py (automated) + scripts/test.sh (pre-deploy)

---

## What this eval is

Evals 01 through 05 are diagnostic.
They tell you WHERE something broke.

Eval 06 is the gate.
It tells you whether to ship.

This eval passes ONLY when evals 01 through 05 all pass
AND the full chain completed within budget.

One failed eval anywhere in the chain — this eval fails.
One BLOCKING failure anywhere — this eval fails.
Over budget on time or cost — this eval fails.

---

## The checklist

**All stages passed:**
- [ ] Eval 01 (intake) passed
- [ ] Eval 02 (quote) passed
- [ ] Eval 03 (emotion) passed — HIGH severity, does not block eval 06
- [ ] Eval 04 (booking) passed
- [ ] Eval 05 (SMS) passed — HIGH severity, does not block eval 06

**Budget compliance:**
- [ ] Total chain wall clock time under 2 minutes
- [ ] Total chain cost under $0.30
- [ ] No individual agent exceeded its budget ceiling

**Data integrity:**
- [ ] No Level 3 failures recorded in `state/decisions/`
- [ ] All 4 artifact files exist and are valid JSON
- [ ] Supabase job record verified (not just self-reported by booking agent)

---

## HIGH severity failures and this gate

Eval 03 (emotion) and Eval 05 (SMS) are HIGH severity — not BLOCKING.
This means:

- A tone failure does NOT fail eval 06
- An SMS failure does NOT fail eval 06

The booking still happened. The customer got booked.
The business needs to follow up manually on the SMS.
But the system worked.

BLOCKING failures (intake and quote) DO fail eval 06.
CRITICAL failures (booking) DO fail eval 06.

---

## How this gate is used in deployment

`scripts/test.sh` runs before every deploy to Railway.
It triggers a test call through the full chain.
If eval 06 fails — the deploy is blocked.

```bash
# From scripts/test.sh
if [ "$EVAL_06_PASS" != "true" ]; then
  echo "DEPLOY BLOCKED — Full chain eval failed."
  echo "Check state/artifacts/ for the eval report."
  exit 1
fi
```

This is not optional.
This is the last line of defense before code reaches production.

---

## Running eval 06 manually

```bash
bash scripts/test.sh
```

This runs:
1. A simulated Vapi webhook (test call with known data)
2. The full planner → quote → booking → evaluator chain
3. All 6 evals
4. Prints a pass/fail report to the terminal
5. Exits 0 on pass, exits 1 on fail

Run this before every deploy.
Run this after every code change to an agent.
Run this if something seems off in production.

---

## The most important thing about this eval

It is not a suggestion.
It is not a nice-to-have.
It is the contract between you and anyone who clones this repo.

If this passes — the system works.
If this fails — the system is not ready.

That's it. That's the whole eval.
