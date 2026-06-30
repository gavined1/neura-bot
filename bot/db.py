import asyncio
import logging
from typing import List, Dict, TypedDict

from supabase import create_client, Client

from bot.config import config

logger = logging.getLogger("neura.db")

_client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

TABLE = "conversations"


class HistoryTurn(TypedDict):
    role: str
    message: str


def _fetch_history_sync(user_id: int, group_id: int, limit: int) -> List[Dict]:
    resp = (
        _client.table(TABLE)
        .select("role, message, created_at")
        .eq("user_id", user_id)
        .eq("group_id", group_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return resp.data or []


def _save_history_sync(user_id: int, group_id: int, role: str, message: str) -> None:
    _client.table(TABLE).insert(
        {
            "user_id": user_id,
            "group_id": group_id,
            "role": role,
            "message": message,
        }
    ).execute()


async def fetch_history(user_id: int, group_id: int, limit: int = None) -> List[HistoryTurn]:
    """
    Returns the last `limit` messages for this exact (user_id, group_id) pair,
    ordered oldest -> newest. Runs the blocking supabase-py call in a worker
    thread so it never stalls the event loop.
    """
    limit = limit or config.HISTORY_LIMIT
    try:
        rows = await asyncio.to_thread(_fetch_history_sync, user_id, group_id, limit)
        rows.reverse()  # oldest -> newest
        return [{"role": r["role"], "message": r["message"]} for r in rows]
    except Exception:
        logger.exception("fetch_history failed user_id=%s group_id=%s", user_id, group_id)
        return []


async def save_history(user_id: int, group_id: int, role: str, message: str) -> None:
    """Inserts a single message row. role must be 'user' or 'assistant'."""
    try:
        await asyncio.to_thread(_save_history_sync, user_id, group_id, role, message)
    except Exception:
        logger.exception("save_history failed user_id=%s group_id=%s", user_id, group_id)