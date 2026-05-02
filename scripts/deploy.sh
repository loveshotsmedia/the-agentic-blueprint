#!/bin/bash

# ─────────────────────────────────────────────────────────────
# deploy.sh — Deploy to Railway
#
# This script:
# 1. Confirms tests pass before deploying
# 2. Checks you're on the main branch
# 3. Pushes to GitHub (Railway auto-deploys from main)
# 4. Confirms the Railway deployment succeeded
#
# USAGE:
#   bash scripts/deploy.sh
#
# NEVER deploy by pushing to GitHub directly.
# Always deploy through this script so the test gate runs.
# ─────────────────────────────────────────────────────────────

set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  THE AGENTIC BLUEPRINT — Deploy to Railway"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Guard: must be in project root ──────────────────────────
if [ ! -f "AGENTS.md" ]; then
  echo "❌ Run from the project root."
  exit 1
fi

# ── Guard: run tests first ───────────────────────────────────
echo "Running quality checks before deploy..."
echo ""

if ! bash scripts/test.sh; then
  echo ""
  echo "❌ DEPLOY BLOCKED — Quality checks failed."
  echo "   Fix the failures above before deploying."
  echo "   This is the eval 06 gate. It exists for a reason."
  exit 1
fi

echo ""
echo "✓ Quality checks passed. Proceeding with deploy."
echo ""

# ── Guard: must be on main branch ───────────────────────────
CURRENT_BRANCH=$(git branch --show-current)

if [ "$CURRENT_BRANCH" != "main" ]; then
  echo "❌ DEPLOY BLOCKED — You are on branch: $CURRENT_BRANCH"
  echo "   Only deploy from main."
  echo "   git checkout main && git merge $CURRENT_BRANCH"
  exit 1
fi

echo "✓ On main branch"

# ── Check for uncommitted changes ───────────────────────────
if [ -n "$(git status --porcelain)" ]; then
  echo ""
  echo "⚠  Uncommitted changes detected:"
  git status --short
  echo ""
  read -p "   Commit and deploy anyway? (y/N): " CONFIRM
  if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Deploy cancelled."
    exit 0
  fi

  git add .
  read -p "   Commit message: " COMMIT_MSG
  git commit -m "$COMMIT_MSG"
fi

# ── Push to GitHub ───────────────────────────────────────────
echo ""
echo "Pushing to GitHub..."
git push origin main
echo "✓ Pushed to GitHub"

# ── Wait for Railway deployment ──────────────────────────────
echo ""
echo "Railway is deploying..."
echo "This typically takes 2-3 minutes."
echo ""

RAILWAY_URL=${RAILWAY_URL:-""}

if [ -n "$RAILWAY_URL" ]; then
  echo "Waiting for health check at: $RAILWAY_URL/health"
  echo ""

  DEPLOY_TIMEOUT=180
  ELAPSED=0
  DEPLOYED=false

  while [ $ELAPSED -lt $DEPLOY_TIMEOUT ]; do
    sleep 10
    ELAPSED=$((ELAPSED + 10))

    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" \
      "$RAILWAY_URL/health" 2>/dev/null || echo "000")

    if [ "$HEALTH" = "200" ]; then
      DEPLOYED=true
      break
    fi

    echo "  Waiting... (${ELAPSED}s / ${DEPLOY_TIMEOUT}s)"
  done

  if [ "$DEPLOYED" = true ]; then
    echo ""
    echo "✓ Deployment confirmed — server is healthy"
    echo ""
    BUSINESS=$(curl -s "$RAILWAY_URL/health" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(d.get('business',''))" \
      2>/dev/null || echo "")
    echo "  Business: $BUSINESS"
    echo "  URL: $RAILWAY_URL"
  else
    echo ""
    echo "⚠  Health check timed out after ${DEPLOY_TIMEOUT}s"
    echo "   Check Railway dashboard for deployment status."
    echo "   https://railway.app/dashboard"
  fi
else
  echo "ℹ  Set RAILWAY_URL in .env to enable automatic health check."
  echo "   Check Railway dashboard for deployment status:"
  echo "   https://railway.app/dashboard"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ✅ DEPLOY COMPLETE"
echo ""
echo "  Demo line: +1 (239) 294-2140"
echo "  Call it to confirm the system is live."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
