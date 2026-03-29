from typing import Set

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_opted_out_user_ids(chat_id: int) -> Set[int]:
    """Return user IDs that opted out for the given chat."""
    abs_chat_id = abs(chat_id)
    result = supabase.table("opted_out_users").select("user_id").eq("chat_id", abs_chat_id).execute()
    return {row["user_id"] for row in result.data or []}
