import asyncio
from collections import defaultdict
from typing import List

from src.scraper import (
    filter_messages_by_importance,
    get_existing_message_ids,
    get_opted_out_user_ids,
    save_messages_batch,
)
from src.scraper.chat_state import upsert_chat_state


class MessageBuffer:
    """Async-safe in-memory buffer that accumulates messages per chat and
    flushes them through the existing scraper pipeline when a threshold
    is reached or a periodic timer fires.

    After each successful flush, ``chat_state.last_message_id`` is updated
    in Supabase so the system always knows where it left off.
    """

    def __init__(self, flush_threshold: int = 1000, flush_interval_seconds: int = 604800):
        self.buffer: dict[int, List[dict]] = defaultdict(list)
        self.flush_threshold = flush_threshold
        self.flush_interval = flush_interval_seconds
        self.lock = asyncio.Lock()

    async def add(self, chat_id: int, message: dict):
        async with self.lock:
            self.buffer[chat_id].append(message)

            if len(self.buffer[chat_id]) >= self.flush_threshold:
                await self._flush_chat(chat_id)

    async def _flush_chat(self, chat_id: int):
        """Process buffered messages through the pipeline and update chat_state.

        Must be called while ``self.lock`` is held.
        """
        messages = self.buffer[chat_id]
        self.buffer[chat_id] = []

        if not messages:
            return

        print(f"🔄 Flushing {len(messages)} buffered messages for chat {chat_id}")

        existing_ids = get_existing_message_ids(chat_id)
        new_messages = [m for m in messages if m["id"] not in existing_ids]

        if not new_messages:
            print(f"✅ All {len(messages)} messages already in DB for chat {chat_id}")
            return

        opted_out_user_ids = get_opted_out_user_ids(chat_id)
        excluded_count = sum(1 for message in new_messages if message.get("author") in opted_out_user_ids)

        if excluded_count:
            print(f"🙈 Opt-out filter: {excluded_count} messages will be excluded from indexing for chat {chat_id}")

        if excluded_count == len(new_messages):
            print(f"✅ No eligible messages after opt-out filter for chat {chat_id}")
            return

        valuable_with_context = filter_messages_by_importance(new_messages, batch_size=20)
        valuable = [message for message in valuable_with_context if message.get("author") not in opted_out_user_ids]

        if not valuable:
            print(f"✅ No valuable messages after AI filter for chat {chat_id}")
            return

        save_messages_batch(valuable, batch_size=10)

        highest_id = max(msg["id"] for msg in valuable)
        upsert_chat_state(chat_id, highest_id)
        print(f"✅ Flushed {len(valuable)} messages for chat {chat_id}, last_message_id={highest_id}")

    async def flush_all(self):
        """Flush every non-empty chat buffer. Called on graceful shutdown and by the periodic timer."""
        async with self.lock:
            for chat_id in list(self.buffer.keys()):
                if self.buffer[chat_id]:
                    await self._flush_chat(chat_id)

    async def periodic_flush(self):
        """Background task that flushes all buffers on a fixed interval."""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush_all()

    @property
    def total_buffered(self) -> int:
        return sum(len(msgs) for msgs in self.buffer.values())
