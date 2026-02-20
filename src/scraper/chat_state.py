from typing import Optional

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_chat_state(chat_id: int) -> Optional[dict]:
    """Fetch chat_state row from Supabase. Returns None if chat has never been scraped."""
    result = supabase.table("chat_state").select("*").eq("chat_id", abs(chat_id)).execute()
    return result.data[0] if result.data else None


def upsert_chat_state(chat_id: int, last_message_id: int, initial_scrape_done: bool = True):
    """Atomically update last_message_id and initial_scrape_done after a successful save."""
    supabase.table("chat_state").upsert(
        {
            "chat_id": abs(chat_id),
            "last_message_id": last_message_id,
            "initial_scrape_done": initial_scrape_done,
            "updated_at": "now()",
        },
        on_conflict="chat_id",
    ).execute()
