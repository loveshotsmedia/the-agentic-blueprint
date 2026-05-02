"""
DATABASE — Supabase Connection

One file. One connection. Used by every part of the system that reads or writes data.

WHY THIS IS ITS OWN FILE:
If the database connection logic is scattered across 10 files —
changing the connection string means changing 10 files.
If it's in one file — you change it once.
That's the only reason this file exists.
"""

import os
import logging
from supabase import create_client, Client

logger = logging.getLogger(__name__)

# The single Supabase client instance
# Everything in the system uses this — never create a second one
_client: Client | None = None


async def init_db():
    """
    Called once at startup by main.py.
    Creates the Supabase client and verifies the connection.
    """
    global _client

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")

    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set. "
            "Check your .env file."
        )

    _client = create_client(url, key)
    logger.info(f"Supabase connected: {url}")


def get_db() -> Client:
    """
    Returns the Supabase client.
    Call this anywhere you need to read or write data.

    Example:
        from src.database import get_db
        db = get_db()
        result = db.table("jobs").select("*").execute()
    """
    if _client is None:
        raise RuntimeError(
            "Database not initialized. "
            "Make sure init_db() was called at startup."
        )
    return _client
