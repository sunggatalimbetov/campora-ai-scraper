import asyncio

from src.realtime import run

CHAT_IDS = [-1001557871268, -1002852524410, -1002842855377, -1001854607533, -1002188551081]


async def main():
    """Phase 1: batch-scrape any new groups, then Phase 2: listen for live messages."""
    await run(chat_ids=CHAT_IDS)


if __name__ == "__main__":
    asyncio.run(main())
