import time
from typing import List

from dotenv import load_dotenv

from src.scraper import get_embedding
from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from supabase import Client, create_client

# Load environment variables
load_dotenv()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def save_messages_batch(messages: List[dict], batch_size: int = 10) -> None:
    """Save messages in batches with embeddings."""
    total = len(messages)

    for i in range(0, total, batch_size):
        batch = messages[i : i + batch_size]

        # Generate embeddings for batch
        for msg in batch:
            try:
                msg["embedding"] = get_embedding(msg["text"])
            except Exception as e:
                print(f"❌ Error generating embedding for message {msg['id']}: {e}")
                continue

        # Save batch to database (upsert on composite PK to handle re-runs gracefully)
        try:
            supabase.table("messages").upsert(batch, on_conflict="id,chat_id").execute()
            print(f"💾 Saved batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({len(batch)} messages)")
        except Exception as e:
            print(f"❌ Error saving batch: {e}")
            # Try saving individually if batch fails
            for msg in batch:
                try:
                    supabase.table("messages").upsert(msg, on_conflict="id,chat_id").execute()
                except Exception as individual_error:
                    print(f"❌ Failed to save message {msg['id']}: {individual_error}")

        # Rate limiting
        time.sleep(1)  # Pause between batches
