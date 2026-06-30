import json
import logging
from typing import Any

import httpx

from .config import settings
from .db import fetch_history, save_user_message, save_assistant_message

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = settings.bot_system_prompt

# Shared async HTTP client with timeouts
_http_client = httpx.AsyncClient(
    timeout=httpx.Timeout(30.0, connect=10.0),
    headers={
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    },
)


async def call_llm(messages: list[dict[str, str]]) -> str:
    """
    Call the LLM API and return the assistant's reply.

    Returns fallback message on any error.
    """
    fallback = "Sorry, I'm having trouble thinking right now. Please try again."

    try:
        payload = {
            "model": settings.llm_model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }
        resp = await _http_client.post(settings.llm_api_url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error("LLM call failed: %s", e)
        return fallback


def build_messages(history: list[dict[str, str]], user_message: str) -> list[dict[str, str]]:
    """
    Build the message list for the LLM API.

    System prompt + history + current user message.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages


async def get_reply(user_id: int, group_id: int, user_message: str) -> str:
    """
    Get AI reply for a user message, with history context.

    Fetches history, builds messages, calls LLM, saves both user and assistant messages.
    """
    # Fetch conversation history
    history = await fetch_history(user_id, group_id)

    # Build messages for LLM
    messages = build_messages(history, user_message)

    # Call LLM
    reply = await call_llm(messages)

    # Save conversation (fire and forget - don't block reply on DB)
    if reply != "Sorry, I'm having trouble thinking right now. Please try again.":
        await save_user_message(user_id, group_id, user_message)
        await save_assistant_message(user_id, group_id, reply)

    return reply