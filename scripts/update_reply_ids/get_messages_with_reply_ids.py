from typing import Any, Dict, List

from telethon import TelegramClient
from telethon.tl.types import Message

from src.config.settings import APP_API_HASH, APP_API_ID, CHAT_USERNAME

client = TelegramClient("update_session", APP_API_ID, APP_API_HASH)


async def get_messages_with_reply_ids() -> List[Dict[str, Any]]:
    """Fetch messages from Telegram and extract reply relationships."""
    print("🔄 Fetching messages from Telegram to get reply relationships...")

    messages_with_replies = []
    total_count = 0

    # Fetch messages with a reasonable limit
    async for msg in client.iter_messages(CHAT_USERNAME):
        msg: Message  # Type hint for IDE support
        total_count += 1

        has_reply_to = msg.reply_to is not None

        message_data = {
            "id": msg.id,
            "reply_to_message_id": (msg.reply_to.reply_to_msg_id if has_reply_to else None),
        }
        messages_with_replies.append(message_data)

        if total_count % 5000 == 0:
            print(f"📊 Processed {total_count} messages...")

    print(f"📊 Total messages processed: {total_count}")
    return messages_with_replies
