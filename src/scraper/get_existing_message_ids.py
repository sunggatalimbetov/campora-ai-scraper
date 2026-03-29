from typing import Set

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_existing_message_ids(chat_id: int) -> Set[int]:
    """Get existing message IDs for a specific chat from database to avoid duplicates."""
    abs_chat_id = abs(chat_id)
    print(f"📋 Fetching existing message for IDs for chat {abs_chat_id}...")

    # Fetch in batches to handle large datasets
    all_ids: Set[int] = set()
    offset = 0
    batch_size = 1000

    while True:
        result = supabase.table("messages").select("id").eq("chat_id", abs_chat_id).range(offset, offset + batch_size - 1).execute()

        if not result.data:
            break

        batch_ids = {msg["id"] for msg in result.data}
        all_ids.update(batch_ids)

        print(f"📋 Loaded {len(batch_ids)} IDs (total: {len(all_ids)})")

        if len(result.data) < batch_size:
            break

        offset += batch_size

    print(f"📋 Found {len(all_ids)} existing messages for chat {abs_chat_id}")
    return all_ids
