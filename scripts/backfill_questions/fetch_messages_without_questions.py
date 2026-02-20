from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def fetch_messages_without_questions(limit: int | None = None) -> list[dict]:
    """Fetch messages that don't yet have generated questions.

    Uses a left-join approach: fetch all message IDs that already appear in
    message_questions, then fetch messages whose IDs are NOT in that set.
    """
    print("📋 Fetching message IDs that already have questions...")
    existing_ids: set[int] = set()
    offset = 0
    batch = 1000

    while True:
        resp = supabase.table("message_questions").select("message_id").range(offset, offset + batch - 1).execute()

        if not resp.data:
            break
        existing_ids.update(r["message_id"] for r in resp.data)
        if len(resp.data) < batch:
            break
        offset += batch

    print(f"  {len(existing_ids)} messages already have questions")

    # Now fetch messages that are NOT in existing_ids
    print("📋 Fetching messages without questions...")
    messages: list[dict] = []
    offset = 0

    while True:
        query = supabase.table("messages").select("id, text").order("id").range(offset, offset + batch - 1)
        resp = query.execute()
        if not resp.data:
            break

        for row in resp.data:
            if row["id"] not in existing_ids:
                messages.append(row)

        if len(resp.data) < batch:
            break
        offset += batch

        # Early exit if we have enough
        if limit and len(messages) >= limit:
            messages = messages[:limit]
            break

    if limit:
        messages = messages[:limit]

    print(f"  {len(messages)} messages need question generations")
    return messages
