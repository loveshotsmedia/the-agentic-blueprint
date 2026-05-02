"""
THE AGENTIC BLUEPRINT — FastAPI Backend
Rich Off AI HVAC

This is the entry point. Every inbound request comes through here.
The app starts, registers all routes, and waits for Vapi to send call events.

WHAT THIS FILE DOES:
- Starts the FastAPI server
- Registers the webhook receiver (Vapi sends call events here)
- Registers the dashboard API routes
- Connects to Supabase on startup
- Verifies all required environment variables are present

WHAT THIS FILE DOES NOT DO:
- Does not contain any agent logic
- Does not generate quotes
- Does not write to the calendar
- Does not send SMS

Each of those jobs belongs to a specific agent in src/agents/
"""

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from src.api.webhooks.vapi import router as vapi_router
from src.api.routes.calls import router as calls_router
from src.api.routes.quotes import router as quotes_router
from src.api.routes.bookings import router as bookings_router
from src.database import init_db

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ── Required environment variables ───────────────────────────────────────────
# If any of these are missing the server will not start.
# Check your .env file against .env.example.
REQUIRED_ENV_VARS = [
    "BUSINESS_NAME",
    "BUSINESS_PHONE",
    "VAPI_API_KEY",
    "VAPI_ASSISTANT_ID",
    "VAPI_WEBHOOK_SECRET",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_SERVICE_KEY",
    "ANTHROPIC_API_KEY",
    "TWILIO_ACCOUNT_SID",
    "TWILIO_AUTH_TOKEN",
    "TWILIO_FROM_NUMBER",
    "GOOGLE_CALENDAR_ID",
    "GOOGLE_SERVICE_ACCOUNT_FILE",
    "WEBHOOK_SECRET",
    "INTERNAL_API_SECRET",
]


def verify_environment():
    """
    Check that every required environment variable is set.
    If anything is missing — log clearly which one and exit.
    Better to fail loudly at startup than silently during a live call.
    """
    missing = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing:
        for var in missing:
            logger.error(f"Missing required environment variable: {var}")
        logger.error(
            "Server cannot start. Fill in the missing variables in your .env file. "
            "See .env.example for descriptions of each variable."
        )
        raise SystemExit(1)
    logger.info("All required environment variables present.")


# ── Lifespan — startup and shutdown ─────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Runs on startup and shutdown.
    Startup: verify env vars, connect to Supabase, log ready state.
    Shutdown: clean up connections.
    """
    # Startup
    logger.info(f"Starting {os.getenv('BUSINESS_NAME', 'The Agentic Blueprint')}...")
    verify_environment()
    await init_db()
    logger.info("Database connected.")
    logger.info(
        f"Server ready. Listening for calls on "
        f"{os.getenv('BUSINESS_PHONE', 'phone number not set')}."
    )
    logger.info(
        f"Adapter routing: "
        f"CRM={os.getenv('CRM_DESTINATION', 'supabase')} | "
        f"Calendar={os.getenv('CALENDAR_DESTINATION', 'google')}"
    )

    yield

    # Shutdown
    logger.info("Server shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="The Agentic Blueprint",
    description=(
        "An AI workforce that answers inbound calls, generates quotes, "
        "and books jobs for field service businesses."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ── CORS ─────────────────────────────────────────────────────────────────────
# Allows the dashboard frontend to talk to this backend.
# In production, replace the wildcard with your actual dashboard URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("DASHBOARD_URL", "http://localhost:3000"),
        "http://localhost:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ───────────────────────────────────────────────────────────────────
# Webhook — Vapi sends call events here
app.include_router(vapi_router, prefix="/webhooks", tags=["webhooks"])

# Dashboard API — the frontend reads from these
app.include_router(calls_router, prefix="/api/calls", tags=["calls"])
app.include_router(quotes_router, prefix="/api/quotes", tags=["quotes"])
app.include_router(bookings_router, prefix="/api/bookings", tags=["bookings"])


# ── Health check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["health"])
async def health_check():
    """
    Railway and monitoring tools ping this endpoint to confirm the server is alive.
    Returns the business name, adapter routing, and server status.
    """
    return {
        "status": "ok",
        "business": os.getenv("BUSINESS_NAME"),
        "crm_destination": os.getenv("CRM_DESTINATION", "supabase"),
        "calendar_destination": os.getenv("CALENDAR_DESTINATION", "google"),
    }


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
    )
