import asyncio
import json
from pathlib import Path

from src.realtime import run

CONFIG_PATH = Path(__file__).parent / "chats.json"


def load_chat_ids() -> list[int]:
    """Load chat IDs from chats.json config file."""
    with open(CONFIG_PATH) as f:
        chats = json.load(f)
    return [chat["chat_id"] for chat in chats]


async def main():
    """Phase 1: batch-scrape any new groups, then Phase 2: listen for live messages."""
    chat_ids = load_chat_ids()
    await run(chat_ids=chat_ids)


if __name__ == "__main__":
    asyncio.run(main())
