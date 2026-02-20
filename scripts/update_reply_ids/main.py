import asyncio

from scripts.update_reply_ids import (
	client,
	get_existing_message_ids,
	get_messages_with_reply_ids,
	update_reply_relationships,
)


async def main():
	"""Main function to update reply relationships."""
	print("🚀 Starting reply relationships update process...")

	async with client:
		# Step 1: Get all messages from Telegram with their reply relationships
		telegram_messages = await get_messages_with_reply_ids()

		# Step 2: Get existing message IDs from database
		existing_ids = get_existing_message_ids()

		# Step 3: Update reply relationships
		update_reply_relationships(telegram_messages, existing_ids)

	print("🎉 Reply relationship update complete!")


if __name__ == "__main__":
	asyncio.run(main())
