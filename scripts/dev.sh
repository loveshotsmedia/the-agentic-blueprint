#!/bin/bash

# ─────────────────────────────────────────────────────────────
# dev.sh — Start the Blueprint locally
#
# Run this every time you open the project to develop.
# Never run commands from memory — always run this script.
#
# USAGE:
#   bash scripts/dev.sh
# ─────────────────────────────────────────────────────────────

set -e  # Stop immediately if any command fails

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  THE AGENTIC BLUEPRINT — Local Dev"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Check we're in the right directory ─────────────────────
if [ ! -f "AGENTS.md" ]; then
  echo "❌ ERROR: Run this from the project root."
  echo "   cd the-agentic-blueprint && bash scripts/dev.sh"
  exit 1
fi

# ── Check .env file exists ──────────────────────────────────
if [ ! -f ".env" ]; then
  echo "❌ ERROR: .env file not found."
  echo "   Copy .env.example to .env and fill in your values."
  echo "   cp .env.example .env"
  exit 1
fi

echo "✓ .env file found"

# ── Check Python is available ───────────────────────────────
if ! command -v python3 &> /dev/null; then
  echo "❌ ERROR: Python 3 not found."
  echo "   Install Python 3.11+ from python.org"
  exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
echo "✓ $PYTHON_VERSION"

# ── Create state directories if they don't exist ────────────
mkdir -p state/traces state/decisions state/artifacts
echo "✓ State directories ready"

# ── Install dependencies ─────────────────────────────────────
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt --quiet
echo "✓ Dependencies installed"

# ── Start the FastAPI server ─────────────────────────────────
echo ""
echo "Starting server..."
echo "API:       http://localhost:8000"
echo "Docs:      http://localhost:8000/docs"
echo "Health:    http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop."
echo ""

python3 -m uvicorn src.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir src
