from typing import List, Optional, Set

from telethon import TelegramClient
from telethon.sessions import StringSession

from src.config.settings import APP_API_HASH, APP_API_ID, TELEGRAM_SESSION

client = TelegramClient(StringSession(TELEGRAM_SESSION), APP_API_ID, APP_API_HASH)


async def fetch_channel_messages(chat_id: int, existing_ids: Set[int], max_id: Optional[int] = None, limit: int = None) -> List[dict]:
    """
    Fetch messages from a Telegram channel/group, skipping those already in database.

    Args:
            chat_id: Chat/group ID (e.g., -1002852524410)
            existing_ids: Set of message IDs already in database
            max_id: Start fetching from this message ID (for resuming)
            limit: Maximum number of messages to fetch (None for all)
    """
    messages = []
    total_count = 0
    filtered_count = 0
    skipped_existing = 0

    # Prepare kwargs for iter_messages
    kwargs = {}
    if max_id:
        kwargs["max_id"] = max_id
    if limit:
        kwargs["limit"] = limit

    print(f"🔄 Starting to fetch messages from chat: {chat_id}")
    if max_id:
        print(f"📍 Resuming from message ID: {max_id}")

    # For supergroups, build a c/ link using the ID without the -100 prefix
    raw_id = str(abs(chat_id))
    if raw_id.startswith("100"):
        raw_id = raw_id[3:]  # strip the "100" prefix for t.me/c/ links
    link_base = f"https://t.me/c/{raw_id}"

    try:
        async for msg in client.iter_messages(chat_id, **kwargs):
            total_count += 1

            # Skip if message already exists in database
            if msg.id in existing_ids:
                skipped_existing += 1
                if total_count % 1000 == 0:
                    print(f"📊 Processed {total_count}, kept {filtered_count}, skipped {skipped_existing} existing")
                continue

            # Keep all messages that have text (AI filter handles importance)
            if msg.text and msg.text.strip():
                messages.append(
                    {
                        "id": msg.id,
                        "chat_id": abs(chat_id),
                        "author": msg.sender_id,
                        "text": msg.text,
                        "link": f"{link_base}/{msg.id}",
                        "reply_to_message_id": msg.reply_to_msg_id,
                    }
                )
                filtered_count += 1

            # Progress updated
            if total_count % 1000 == 0:
                print(f"📊 Processed {total_count}, kept {filtered_count}, skipped {skipped_existing} existing")

            # Optional: Break if we've collected enough new messages
            if limit and filtered_count >= limit:
                break
    except Exception as e:
        print(f"❌ Error fetching messages: {e}")

    print(f"📊 Final stats: {total_count} processed, {filtered_count} new quality messages, {skipped_existing} skipped (existing)")
    return messages
