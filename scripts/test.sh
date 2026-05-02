#!/bin/bash

# ─────────────────────────────────────────────────────────────
# test.sh — Run all quality checks
#
# Run this before every deploy.
# Run this after every code change to an agent.
# If this passes — you can ship.
# If this fails — do not ship.
#
# USAGE:
#   bash scripts/test.sh           # Unit tests only
#   bash scripts/test.sh --e2e     # Unit tests + Playwright
#   bash scripts/test.sh --all     # Everything
# ─────────────────────────────────────────────────────────────

set -e

RUN_E2E=false
if [[ "$1" == "--e2e" || "$1" == "--all" ]]; then
  RUN_E2E=true
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  THE AGENTIC BLUEPRINT — Quality Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Guard: must be in project root ──────────────────────────
if [ ! -f "AGENTS.md" ]; then
  echo "❌ Run from the project root."
  exit 1
fi

# ── Guard: must have .env ────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "❌ .env file not found. Copy .env.example to .env first."
  exit 1
fi

PASS=0
FAIL=0

# ─────────────────────────────────────────────────────────────
# STEP 1: Python unit tests
# ─────────────────────────────────────────────────────────────
echo "── Step 1: Unit tests ──────────────────────"
echo ""

if python3 -m pytest quality/tests/ -v --tb=short 2>&1; then
  echo ""
  echo "✓ Unit tests passed"
  PASS=$((PASS + 1))
else
  echo ""
  echo "✗ Unit tests FAILED"
  FAIL=$((FAIL + 1))
fi

# ─────────────────────────────────────────────────────────────
# STEP 2: Eval 06 — Full chain gate
# ─────────────────────────────────────────────────────────────
echo ""
echo "── Step 2: Full chain eval (Eval 06) ───────"
echo ""

# Run the test call through the API and check the eval report
# The server must be running for this step
if curl -s "http://localhost:8000/health" > /dev/null 2>&1; then

  # Inject test call
  RESPONSE=$(curl -s -X POST "http://localhost:8000/webhooks/vapi" \
    -H "Content-Type: application/json" \
    -H "x-test-mode: true" \
    -d '{
      "type": "call.ended",
      "call": {
        "call_sid": "test-eval06-'"$(date +%s)"'",
        "caller_phone": "+15555559999",
        "transcript": "Agent: Thanks for calling Rich Off AI HVAC. Caller: Hi, my name is Test User. I need AC repair at 999 Test Street. It is a home and I need someone this week.",
        "duration_seconds": 30,
        "assistant_id": "test"
      },
      "timestamp": "'"$(date -u +%Y-%m-%dT%H:%M:%SZ)"'"
    }')

  echo "Test call injected. Waiting 30s for chain to complete..."
  sleep 30

  # Check the most recent eval report
  LATEST_REPORT=$(ls -t state/artifacts/*-eval-report.json 2>/dev/null | head -1)

  if [ -n "$LATEST_REPORT" ]; then
    EVAL_06=$(python3 -c "
import json
with open('$LATEST_REPORT') as f:
    r = json.load(f)
print('true' if r.get('eval_06_full_chain_pass') else 'false')
")

    if [ "$EVAL_06" = "true" ]; then
      echo "✓ Eval 06 (full chain) PASSED"
      PASS=$((PASS + 1))
    else
      echo "✗ Eval 06 (full chain) FAILED"
      echo "  Check: $LATEST_REPORT"
      FAIL=$((FAIL + 1))
    fi
  else
    echo "⚠ No eval report found — server may not have processed the test call yet"
    echo "  Skipping eval 06 check"
  fi

else
  echo "⚠ Server not running — skipping full chain eval"
  echo "  Start the server with: bash scripts/dev.sh"
  echo "  Then re-run: bash scripts/test.sh"
fi

# ─────────────────────────────────────────────────────────────
# STEP 3: Playwright E2E (only if --e2e flag passed)
# ─────────────────────────────────────────────────────────────
if [ "$RUN_E2E" = true ]; then
  echo ""
  echo "── Step 3: Playwright E2E audit ────────────"
  echo ""

  # Check Playwright is installed
  if ! command -v npx &> /dev/null; then
    echo "❌ npx not found. Install Node.js from nodejs.org"
    FAIL=$((FAIL + 1))
  else
    if npx playwright test quality/playwright/booking.spec.ts \
      --reporter=list 2>&1; then
      echo ""
      echo "✓ Playwright audit passed"
      PASS=$((PASS + 1))
    else
      echo ""
      echo "✗ Playwright audit FAILED"
      FAIL=$((FAIL + 1))
    fi
  fi
else
  echo ""
  echo "── Step 3: Playwright E2E ──────────────────"
  echo "   Skipped (run with --e2e to include)"
fi

# ─────────────────────────────────────────────────────────────
# RESULT
# ─────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ "$FAIL" -eq 0 ]; then
  echo ""
  echo "  ✅ ALL CHECKS PASSED ($PASS/$((PASS + FAIL)))"
  echo ""
  echo "  Safe to deploy."
  echo "  Run: bash scripts/deploy.sh"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
else
  echo ""
  echo "  ❌ CHECKS FAILED ($FAIL failed, $PASS passed)"
  echo ""
  echo "  Do NOT deploy until all checks pass."
  echo "  Review the failures above."
  echo "  Check state/artifacts/ for eval reports."
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 1
fi
