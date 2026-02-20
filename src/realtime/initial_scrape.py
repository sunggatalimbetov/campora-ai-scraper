from src.scraper import (
    fetch_channel_messages,
    filter_messages_by_importance,
    get_existing_message_ids,
    save_messages_batch,
)
from src.scraper.chat_state import get_chat_state, upsert_chat_state


async def initial_scrape(chat_id: int, batch_size: int = 10):
    """Full-history batch scrape for a chat group that hasn't been scraped yet.

    Checks ``chat_state`` to decide whether to run.  If the chat has already
    been fully scraped (``initial_scrape_done=True``), this is a no-op.
    If a previous attempt was interrupted, it resumes from ``last_message_id``.

    After a successful save, ``chat_state`` is updated so restarts pick up
    where we left off.
    """
    state = get_chat_state(chat_id)

    if state and state["initial_scrape_done"]:
        print(f"✅ Chat {abs(chat_id)} already scraped, skipping initial fetch")
        return

    resume_from = state["last_message_id"] if state else None
    if resume_from:
        print(f"📍 Resuming initial scrape for chat {abs(chat_id)} from message ID {resume_from}")

    existing_ids = get_existing_message_ids(chat_id)
    new_messages = await fetch_channel_messages(chat_id, existing_ids, max_id=resume_from, limit=None)

    if not new_messages:
        upsert_chat_state(abs(chat_id), resume_from or 0, initial_scrape_done=True)
        print(f"✅ No new messages for chat {abs(chat_id)}, marked as done")
        return

    before_count = len(new_messages)
    valuable = filter_messages_by_importance(new_messages, batch_size=20)
    after_count = len(valuable)
    print(f"🤖 AI filter: {before_count} -> {after_count} valuable ({before_count - after_count} filtered out)")

    if not valuable:
        upsert_chat_state(abs(chat_id), resume_from or 0, initial_scrape_done=True)
        print(f"✅ No valuable messages for chat {abs(chat_id)}, marked as done")
        return

    save_messages_batch(valuable, batch_size=batch_size)

    highest_id = max(msg["id"] for msg in valuable)
    upsert_chat_state(abs(chat_id), highest_id, initial_scrape_done=True)
    print(f"✅ Initial scrape done for chat {abs(chat_id)}, last_message_id={highest_id}")
