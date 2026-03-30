"""Batch-fetch reply parent texts for a chunk of messages."""

from supabase import Client


def fetch_reply_parents_batch(
    messages: list[dict],
    chat_id: int,
    supabase: Client,
) -> dict[int, str]:
    """Fetch parent message texts for all replies in a chunk.

    Args:
        messages: List of message dicts with 'reply_to_message_id' field.
        chat_id: Chat ID to scope the lookup.
        supabase: Supabase client.

    Returns:
        Dict mapping parent_message_id -> parent text (truncated to 300 chars).
    """
    parent_ids = [
        m["reply_to_message_id"]
        for m in messages
        if m.get("reply_to_message_id")
    ]

    if not parent_ids:
        return {}

    unique_ids = list(set(parent_ids))

    # Supabase .in_() has a practical limit; batch if needed
    parents: dict[int, str] = {}
    batch_size = 500
    for i in range(0, len(unique_ids), batch_size):
        batch = unique_ids[i : i + batch_size]
        resp = (
            supabase.table("messages")
            .select("id, text")
            .eq("chat_id", chat_id)
            .in_("id", batch)
            .execute()
        )
        for row in resp.data:
            if row.get("text"):
                parents[row["id"]] = row["text"][:300]

    return parents
