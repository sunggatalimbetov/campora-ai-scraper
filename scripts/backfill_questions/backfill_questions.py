import time

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from scripts.backfill_questions import fetch_messages_without_questions
from scripts.backfill_questions.questions_generator import (
    generate_questions_for_message,
)
from src.scraper.get_embedding import get_embedding
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def backfill(
    batch_size: int = 10,
    delay: float = 1.0,
    limit: int | None = None,
) -> None:
    """Generate and store questions for messages that don't have them yet."""
    messages = fetch_messages_without_questions(limit)

    if not messages:
        print("✅ All messages already have questions. Nothing to do.")
        return

    total = len(messages)
    processed = 0
    skipped = 0
    errored = 0
    questions_created = 0

    print(f"\n🚀 Processing {total} messages in batches of {batch_size}\n")

    for i in range(0, total, batch_size):
        batch = messages[i : i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size

        print(f"── Batch {batch_num}/{total_batches} ({len(batch)} messages) ──")

        for msg in batch:
            msg_id = msg["id"]
            text = msg.get("text", "")

            if not text or not text.strip():
                skipped += 1
                continue

            try:
                # 1. Generate questions
                questions = generate_questions_for_message(text)

                if not questions:
                    skipped += 1
                    continue

                # 2. For each question, compute embedding and insert
                for q_text in questions:
                    q_embedding = get_embedding(q_text)
                    supabase.table("message_questions").insert(
                        {
                            "message_id": msg_id,
                            "question_text": q_text,
                            "embedding": q_embedding,
                        }
                    ).execute()
                    questions_created += 1

                processed += 1
                print(f" ✅ msg {msg_id}: {len(questions)} questions generated")
            except Exception as e:
                errored += 1
                print(f" ❌ msg {msg_id}: {e}")

        # Progress summary
        done = processed + skipped + errored
        print(f"  Progress: {done}/{total} " f"(✅ {processed} | ⏭️ {skipped} | ❌ {errored}) " f"| questions created: {questions_created}")

        # Rate limiting between batches
        if i + batch_size < total:
            time.sleep(delay)

    print(f"\n{'=' * 50}")
    print("BACKFILL COMPLETE")
    print(f"  Messages processed:   {processed}")
    print(f"  Messages skipped:     {skipped}")
    print(f"  Messages errored:     {errored}")
    print(f"  Questions created:    {questions_created}")
    print(f"{'=' * 50}")
