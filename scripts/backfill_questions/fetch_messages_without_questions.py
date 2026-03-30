from typing import Optional

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def fetch_messages_without_questions(
    limit: Optional[int] = None,
    chat_id: Optional[int] = None,
) -> list[dict]:
    """Fetch messages that don't yet have generated questions.

    Uses a left-join approach: fetch all (message_id, chat_id) pairs that
    already appear in message_questions, then fetch messages whose composite
    key is NOT in that set.

    Args:
        limit: Maximum number of messages to return.
        chat_id: If provided, only fetch messages from this chat.
    """
    print("📋 Fetching message IDs that already have questions...")
    existing_keys: set[tuple[int, int]] = set()
    offset = 0
    batch = 1000

    while True:
        query = supabase.table("message_questions").select("message_id, chat_id")
        if chat_id is not None:
            query = query.eq("chat_id", chat_id)
        resp = query.range(offset, offset + batch - 1).execute()

        if not resp.data:
            break
        existing_keys.update(
            (r["message_id"], r["chat_id"]) for r in resp.data
        )
        if len(resp.data) < batch:
            break
        offset += batch

    print(f"  {len(existing_keys)} messages already have questions")

    # Now fetch messages that are NOT in existing_keys
    print("📋 Fetching messages without questions...")
    messages: list[dict] = []
    offset = 0

    while True:
        query = (
            supabase.table("messages")
            .select("id, chat_id, text, reply_to_message_id")
            .order("id")
        )
        if chat_id is not None:
            query = query.eq("chat_id", chat_id)
        resp = query.range(offset, offset + batch - 1).execute()
        if not resp.data:
            break

        for row in resp.data:
            if (row["id"], row["chat_id"]) not in existing_keys:
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

    print(f"  {len(messages)} messages need question generation")
    return messages
