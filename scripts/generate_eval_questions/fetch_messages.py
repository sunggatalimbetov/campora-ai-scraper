from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client  # noqa: E402

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def fetch_messages(limit: int = 1000) -> list[dict]:
    """Fetch messages from the database"""
    print(f"Fetching {limit} messages from database...")

    all_messages = []
    offset = 0
    batch_size = 500

    while len(all_messages) < limit:
        fetch_count = min(batch_size, limit - len(all_messages))
        result = supabase.table("messages").select("id, text").order("id", desc=True).range(offset, offset + fetch_count - 1).execute()

        if not result.data:
            break

        all_messages.extend(result.data)
        print(f"  Fetched {len(result.data)} messages (total: {len(all_messages)})")

        if len(result.data) < fetch_count:
            break

        offset += fetch_count

    print(f"Total messages fetched: {len(all_messages)}")
    return all_messages
