from typing import Optional

from src.scraper import (
    fetch_channel_messages,
    filter_messages_by_importance,
    get_existing_message_ids,
    save_messages_batch,
)


async def scrape_channel(chat_id: int, max_id: Optional[int] = None, limit: Optional[int] = None, batch_size: int = 10) -> None:
    """
    Main function to scrape a Telegram channel/group.

    Args:
            chat_id: Chat/group ID (e.g., -1002852524410)
            max_id: Start from this message ID (for resuming)
            limit: Maximum number of new messages to process
            batch_size: Number of messages to save at once
    """
    # Get existing message IDs to avoid duplicates (scoped to this chat)
    existing_ids = get_existing_message_ids(chat_id)

    # Fetch new messages from channel
    new_messages = await fetch_channel_messages(chat_id, existing_ids, max_id=max_id, limit=limit)

    if not new_messages:
        print("✅ No new messages to process")
        return

    # AI importance filtering (batches of 20)
    before_count = len(new_messages)
    valuable_messages = filter_messages_by_importance(new_messages, batch_size=20)
    after_count = len(valuable_messages)
    print(f"🤖 AI filter: {before_count} messages -> {after_count} valuable ({before_count - after_count} filtered out)")

    if not valuable_messages:
        print("✅ No valuable messages to save after filtering")
        return

    print(f"💾 Starting to save {len(valuable_messages)} new messages...")

    # Save messages in batches (with embeddings)
    save_messages_batch(valuable_messages, batch_size)

    print("✅ Channel scraping completed successfully!")

    # Print the ID of the last message for resuming
    if valuable_messages:
        last_id = min(msg["id"] for msg in valuable_messages)  # Telegram IDs are descending
        print(f"📍 To resume from where you left off, use max_id={last_id}")
