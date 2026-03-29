def build_message_link(chat_id: int, message_id: int) -> str:
    """Build a Telegram t.me/c link for a supergroup message."""
    raw_chat_id = str(abs(chat_id))
    # Telethon exposes supergroup chat IDs as -100<internal_id>, while
    # t.me/c links expect just the internal_id portion.
    if raw_chat_id.startswith("100"):
        raw_chat_id = raw_chat_id[3:]
    return f"https://t.me/c/{raw_chat_id}/{message_id}"
