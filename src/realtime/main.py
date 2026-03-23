import asyncio
from typing import List

from telethon import events

from src.scraper import client
from src.realtime.initial_scrape import initial_scrape
from src.realtime.message_buffer import MessageBuffer
from src.realtime.pre_filter import should_buffer
from src.realtime.signal_handlers import setup_signal_handlers


async def run(chat_ids: List[int], flush_threshold: int = 1000, flush_interval: int = 604800):
    """Two-phase entry point: initial batch scrape, then real-time event listener.

    Phase 1 — for each chat_id, run a full-history batch scrape if the chat
    hasn't been scraped before (checked via ``chat_state`` table).

    Phase 2 — register a Telethon ``NewMessage`` event handler that buffers
    incoming messages and flushes them through the pipeline when a threshold
    is reached or a periodic timer fires.
    """
    async with client:
        # ── Phase 1: initial scrape for any new groups ──────────────────
        for chat_id in chat_ids:
            print(f"\n🚀 Checking chat {abs(chat_id)}...")
            await initial_scrape(chat_id)

        # ── Phase 2: real-time listener ─────────────────────────────────
        buffer = MessageBuffer(
            flush_threshold=flush_threshold,
            flush_interval_seconds=flush_interval,
        )
        setup_signal_handlers(buffer, client)
        asyncio.create_task(buffer.periodic_flush())

        @client.on(events.NewMessage(chats=chat_ids))
        async def on_new_message(event):
            msg = event.message
            if not (msg.text and msg.text.strip()):
                return
            if not should_buffer(msg.text):
                return

            raw_id = str(abs(event.chat_id))
            if raw_id.startswith("100"):
                raw_id = raw_id[3:]

            await buffer.add(
                chat_id=abs(event.chat_id),
                message={
                    "id": msg.id,
                    "chat_id": abs(event.chat_id),
                    "author": msg.sender_id,
                    "text": msg.text,
                    "link": f"https://t.me/c/{raw_id}/{msg.id}",
                    "reply_to_message_id": msg.reply_to_msg_id,
                    "created_at": msg.date.isoformat() if msg.date else None,
                },
            )

        print(f"\n👂 Listening for new messages across {len(chat_ids)} chats...")
        await client.run_until_disconnected()
