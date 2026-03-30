import time
from typing import List, Set, Tuple

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Keyed by abs(chat_id) -> (user_ids, monotonic timestamp).
# Grows with the number of distinct chats — bounded in practice by the
# small number of monitored groups.
_cache: dict[int, Tuple[Set[int], float]] = {}
_CACHE_TTL_SECONDS = 300


def get_opted_out_user_ids(chat_id: int) -> Set[int]:
    """Return user IDs that opted out for the given chat.

    Results are cached for 5 minutes to avoid repeated DB round-trips
    during a single scrape run.
    """
    abs_chat_id = abs(chat_id)
    now = time.monotonic()

    cached = _cache.get(abs_chat_id)
    if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
        return cached[0]

    result = supabase.table("opted_out_users").select("user_id").eq("chat_id", abs_chat_id).execute()
    user_ids = {row["user_id"] for row in result.data or []}
    _cache[abs_chat_id] = (user_ids, now)
    return user_ids


def filter_opted_out(messages: List[dict], chat_id: int) -> Tuple[List[dict], int]:
    """Remove messages from opted-out users.

    Returns (eligible_messages, excluded_count).
    """
    opted_out = get_opted_out_user_ids(chat_id)
    eligible = [m for m in messages if m.get("author") not in opted_out]
    return eligible, len(messages) - len(eligible)


def invalidate_cache(chat_id: int | None = None):
    """Clear the opted-out cache. Pass a chat_id to clear one entry, or None to clear all."""
    if chat_id is None:
        _cache.clear()
    else:
        _cache.pop(abs(chat_id), None)
