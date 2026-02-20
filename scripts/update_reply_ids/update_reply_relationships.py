from typing import Any, Dict, List

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def update_reply_relationships(telegram_messages: List[Dict[str, Any]], existing_ids: List[int]):
	"""Update reply_to_message_id for existing messages in database."""
	print("🔄 Updating reply relationships in database...")

	# Creating a mapping of message_id -> reply_to_message_id from Telegram data
	reply_mapping = {}
	for msg in telegram_messages:
		if msg["id"] in existing_ids:  # Only for messages that exist in our DB
			reply_mapping[msg["id"]] = msg["reply_to_message_id"]

	updated_count = 0
	batch_size = 100

	# Process in batches
	message_ids = list(reply_mapping.keys())
	print(f"📊 Will update {len(message_ids)} messages")

	for i in range(0, len(message_ids), batch_size):
		batch_ids = message_ids[i : i + batch_size]

		# Update each message in the batch
		for msg_id in batch_ids:
			reply_to_id = reply_mapping[msg_id]

			try:
				supabase.table("messages").update({"reply_to_message_id": reply_to_id}).eq("id", msg_id).execute()

				updated_count += 1

				if updated_count % 100 == 0:
					print(f"💾 Updated {updated_count}/{len(message_ids)} messages...")
			except Exception as e:
				print(f"❌ Error updating message {msg_id}: {e}")

	print(f"✅ Successfully updated {updated_count} messages with reply relationships")
