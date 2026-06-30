import logging
from typing import Any

from supabase import create_client, Client

from .config import settings

logger = logging.getLogger(__name__)

_supabase: Client | None = None


def get_supabase() -> Client:
    """Get or create Supabase client singleton."""
    global _supabase
    if _supabase is None:
        _supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase


async def fetch_history(user_id: int, group_id: int, limit: int = 10) -> list[dict[str, str]]:
    """
    Fetch last N messages for a (user_id, group_id) pair.

    Returns list of dicts with 'role' and 'content' keys for LLM consumption.
    """
    supabase = get_supabase()
    try:
        resp = (
            supabase.table("conversations")
            .select("role, message")
            .eq("user_id", user_id)
            .eq("group_id", group_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        # Supabase returns newest first; reverse for chronological order
        messages = [{"role": row["role"], "content": row["message"]} for row in reversed(resp.data)]
        return messages
    except Exception as e:
        logger.error("Failed to fetch history for user=%s group=%s: %s", user_id, group_id, e)
        return []


async def save_message(user_id: int, group_id: int, role: str, message: str) -> bool:
    """
    Save a single message to conversation history.

    Returns True on success, False on failure (errors are logged, not raised).
    """
    if role not in ("user", "assistant"):
        logger.error("Invalid role '%s' for user=%s group=%s", role, user_id, group_id)
        return False

    supabase = get_supabase()
    try:
        supabase.table("conversations").insert({
            "user_id": user_id,
            "group_id": group_id,
            "role": role,
            "message": message,
        }).execute()
        return True
    except Exception as e:
        logger.error("Failed to save message for user=%s group=%s role=%s: %s", user_id, group_id, role, e)
        return False


async def save_user_message(user_id: int, group_id: int, message: str) -> bool:
    """Convenience wrapper for saving user messages."""
    return await save_message(user_id, group_id, "user", message)


async def save_assistant_message(user_id: int, group_id: int, message: str) -> bool:
    """Convenience wrapper for saving assistant messages."""
    return await save_message(user_id, group_id, "assistant", message)