import asyncio

from src.scraper import client, scrape_channel


async def main():
    """Scrape messages from multiple Telegram groups."""

    # Group chat IDs to scrape
    CHAT_IDS = [-1001557871268, -1002852524410, -1002842855377, -1001854607533, -1002188551081]
    MAX_ID = None
    LIMIT = None
    BATCH_SIZE = 10

    async with client:
        for chat_id in CHAT_IDS:
            print(f"\n🚀 Starting scraper for chat: {chat_id}")
            await scrape_channel(chat_id=chat_id, max_id=MAX_ID, limit=LIMIT, batch_size=BATCH_SIZE)

    print("\n✅ All channels scraped!")


if __name__ == "__main__":
    asyncio.run(main())
