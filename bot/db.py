import asyncio
import logging
import time
from collections import OrderedDict
from typing import List, Dict, TypedDict

from supabase import create_client, Client

from bot.config import config

logger = logging.getLogger("neura.db")

_client: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

_history_cache: OrderedDict[tuple[int, int], dict] = OrderedDict()
MAX_CACHE_SIZE = 1000

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
    requested_limit = limit or config.HISTORY_LIMIT

    # Check cache
    if requested_limit <= config.HISTORY_LIMIT:
        key = (user_id, group_id)
        if key in _history_cache:
            entry = _history_cache[key]
            if time.time() - entry["timestamp"] < config.HISTORY_CACHE_TTL_SECONDS:
                _history_cache.move_to_end(key)
                return list(entry["history"][-requested_limit:])

    try:
        fetch_limit = max(requested_limit, config.HISTORY_LIMIT)
        rows = await asyncio.to_thread(_fetch_history_sync, user_id, group_id, fetch_limit)
        rows.reverse()  # oldest -> newest
        history = [{"role": r["role"], "message": r["message"]} for r in rows]

        # Cache the most recent config.HISTORY_LIMIT turns
        key = (user_id, group_id)
        _history_cache[key] = {
            "timestamp": time.time(),
            "history": list(history[-config.HISTORY_LIMIT:])
        }
        _history_cache.move_to_end(key)
        if len(_history_cache) > MAX_CACHE_SIZE:
            _history_cache.popitem(last=False)

        return list(history[-requested_limit:])
    except Exception:
        logger.exception("fetch_history failed user_id=%s group_id=%s", user_id, group_id)
        return []


async def save_history(user_id: int, group_id: int, role: str, message: str) -> None:
    """Inserts a single message row. role must be 'user' or 'assistant'."""
    try:
        await asyncio.to_thread(_save_history_sync, user_id, group_id, role, message)

        # Update cache if key exists
        key = (user_id, group_id)
        if key in _history_cache:
            entry = _history_cache[key]
            entry["history"].append({"role": role, "message": message})
            if len(entry["history"]) > config.HISTORY_LIMIT:
                entry["history"] = entry["history"][-config.HISTORY_LIMIT:]
            entry["timestamp"] = time.time()
            _history_cache.move_to_end(key)
    except Exception:
        logger.exception("save_history failed user_id=%s group_id=%s", user_id, group_id)