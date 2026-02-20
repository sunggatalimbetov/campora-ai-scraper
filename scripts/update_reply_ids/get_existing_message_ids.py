from typing import List

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def get_existing_message_ids() -> List[int]:
	"""Get all message IDs that exist in our database."""
	print("📋 Getting existing message IDs from database...")

	response = supabase.table("messages").select("id").execute()
	existing_ids = [row["id"] for row in response.data]

	print(f"📊 Found {len(existing_ids)} existing messages in database")
	return existing_ids
