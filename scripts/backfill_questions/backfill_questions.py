"""Chunked backfill orchestrator for message questions using Groq + OpenAI embeddings."""

import time
from typing import Optional

from src.config.settings import SUPABASE_SERVICE_KEY, SUPABASE_URL
from scripts.backfill_questions.groq_client import GroqQuestionGenerator
from scripts.backfill_questions.batch_embeddings import get_embeddings_batch
from scripts.backfill_questions.reply_context import fetch_reply_parents_batch
from scripts.backfill_questions.checkpoint import load_checkpoint, save_checkpoint
from supabase import Client, create_client

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def backfill(
    chat_id: int,
    chunk_size: int = 1000,
    groq_batch_size: int = 25,
    resume: bool = False,
    dry_run: bool = False,
    limit: Optional[int] = None,
) -> None:
    """Generate and store questions for messages using chunked Groq pipeline.

    Args:
        chat_id: Positive chat ID to process.
        chunk_size: Messages per DB fetch chunk.
        groq_batch_size: Messages per Groq API call.
        resume: Resume from last checkpoint.
        dry_run: Generate questions but skip embedding and DB insert.
        limit: Max total messages to process.
    """
    generator = GroqQuestionGenerator()

    cursor = 0
    total_processed = 0
    total_questions = 0
    start_time = time.time()

    if resume:
        cp = load_checkpoint(chat_id)
        if cp:
            cursor = cp["last_message_id"]
            total_processed = cp["messages_processed"]
            total_questions = cp["questions_generated"]
            print(f"📍 Resuming from checkpoint: message_id > {cursor} "
                  f"({total_processed} processed, {total_questions} questions)")
        else:
            print("📍 No checkpoint found, starting from beginning")

    print(f"\n🚀 Backfill for chat_id={chat_id} "
          f"(chunk={chunk_size}, groq_batch={groq_batch_size}, "
          f"dry_run={dry_run})\n")

    chunk_num = 0

    while True:
        # 1. Fetch chunk of messages
        fetch_limit = chunk_size
        if limit:
            remaining = limit - total_processed
            fetch_limit = min(chunk_size, remaining)

        resp = (
            supabase.table("messages")
            .select("id, chat_id, text, reply_to_message_id")
            .eq("chat_id", chat_id)
            .gt("id", cursor)
            .order("id")
            .limit(fetch_limit)
            .execute()
        )

        messages = resp.data
        if not messages:
            break

        chunk_num += 1
        chunk_start = time.time()
        print(f"── Chunk {chunk_num} ({len(messages)} messages, cursor > {cursor}) ──")

        # 2. Batch-fetch reply parent texts
        parents = fetch_reply_parents_batch(messages, chat_id, supabase)
        replies_found = sum(1 for m in messages if m.get("reply_to_message_id") in parents)
        if replies_found:
            print(f"  📎 Reply context: {replies_found} messages have parent text")

        # 3. Build enriched message list
        enriched = []
        for m in messages:
            entry = {"id": m["id"], "chat_id": m["chat_id"], "text": m.get("text", "")}
            parent_id = m.get("reply_to_message_id")
            if parent_id and parent_id in parents:
                entry["reply_context"] = parents[parent_id]
            enriched.append(entry)

        # Filter out empty and low-value messages
        # Skip short messages (<15 chars) unless they have reply context
        # (short replies like "14-15 августа" or "127" are valuable with context)
        enriched = [
            e for e in enriched
            if e["text"] and e["text"].strip()
            and (len(e["text"].strip()) >= 15 or e.get("reply_context"))
        ]

        # 4. Generate questions in groq batches
        all_questions: list[tuple[int, int, str]] = []  # (message_id, chat_id, question_text)
        skipped = len(messages) - len(enriched)

        for i in range(0, len(enriched), groq_batch_size):
            batch = enriched[i : i + groq_batch_size]
            batch_num = i // groq_batch_size + 1
            total_batches = (len(enriched) + groq_batch_size - 1) // groq_batch_size

            result = generator.generate_questions_batch(batch)

            batch_q_count = sum(len(qs) for qs in result.values())
            coverage = len(result) / len(batch) if batch else 0
            print(f"  🔄 Groq batch {batch_num}/{total_batches}: "
                  f"{len(result)}/{len(batch)} messages → {batch_q_count} questions")
            if coverage < 0.5:
                print(f"  ⚠️ Low coverage ({coverage:.0%}) — possible truncation or parse failure")

            id_to_chat = {m["id"]: m["chat_id"] for m in batch}
            for msg_id, questions in result.items():
                for q_text in questions:
                    all_questions.append((msg_id, id_to_chat.get(msg_id, chat_id), q_text))

        # Count messages that actually got questions
        msgs_with_questions = len(set(mq[0] for mq in all_questions))
        msgs_skipped_by_llm = len(enriched) - msgs_with_questions
        chunk_processed = len(enriched)
        chunk_questions = len(all_questions)

        if dry_run:
            print(f"  🏜️ DRY RUN: would embed {chunk_questions} questions and insert to DB")
            if all_questions:
                print("\n  === Generated Questions ===")
                current_msg = None
                for msg_id, _, q in all_questions:
                    if msg_id != current_msg:
                        msg_text = next(
                            (m["text"] for m in enriched if m["id"] == msg_id), "?"
                        )
                        print(f"\n  MSG {msg_id}: {msg_text}")
                        current_msg = msg_id
                    print(f"    → {q}")
                print()
        elif all_questions:
            # 5. Skip messages that already have questions (dedup on re-run)
            chunk_msg_ids = list(set(q[0] for q in all_questions))
            already_covered: set[int] = set()
            dedup_batch_size = 500
            for i in range(0, len(chunk_msg_ids), dedup_batch_size):
                batch_ids = chunk_msg_ids[i : i + dedup_batch_size]
                existing_resp = (
                    supabase.table("message_questions")
                    .select("message_id")
                    .eq("chat_id", chat_id)
                    .in_("message_id", batch_ids)
                    .execute()
                )
                already_covered.update(r["message_id"] for r in existing_resp.data)
            if already_covered:
                before = len(all_questions)
                all_questions = [q for q in all_questions if q[0] not in already_covered]
                print(f"  ⏭️ Skipped {before - len(all_questions)} questions "
                      f"({len(already_covered)} messages already in DB)")

            if not all_questions:
                print(f"  ⏭️ All messages in this chunk already have questions")
            else:
                # 6. Batch embed all question texts
                question_texts = [q[2] for q in all_questions]
                print(f"  📦 Embedding {len(question_texts)} questions...")
                embeddings = get_embeddings_batch(question_texts)

                # 7. Batch insert into message_questions
                rows = [
                    {
                        "message_id": all_questions[j][0],
                        "chat_id": all_questions[j][1],
                        "question_text": all_questions[j][2],
                        "embedding": embeddings[j],
                    }
                    for j in range(len(all_questions))
                ]

                insert_batch_size = 500
                for i in range(0, len(rows), insert_batch_size):
                    batch = rows[i : i + insert_batch_size]
                    supabase.table("message_questions").insert(batch).execute()

                print(f"  💾 Inserted {len(rows)} questions to DB")

        # 7. Update counters and checkpoint
        total_processed += chunk_processed
        total_questions += chunk_questions
        cursor = messages[-1]["id"]

        if not dry_run:
            save_checkpoint(chat_id, cursor, total_processed, total_questions)

        # Progress
        elapsed = time.time() - start_time
        chunk_time = time.time() - chunk_start
        rate = total_processed / elapsed if elapsed > 0 else 0
        print(f"  ✅ Chunk done in {chunk_time:.1f}s | "
              f"Total: {total_processed} msgs, {total_questions} questions | "
              f"Rate: {rate:.0f} msgs/s | "
              f"Got questions: {msgs_with_questions}/{chunk_processed} | "
              f"Skipped (empty text): {skipped} | "
              f"Skipped (low-info): {msgs_skipped_by_llm}")

        # Check limit
        if limit and total_processed >= limit:
            print(f"\n⏹️ Reached limit of {limit} messages")
            break

    elapsed = time.time() - start_time
    print(f"\n{'=' * 50}")
    print("BACKFILL COMPLETE")
    print(f"  Messages processed:   {total_processed}")
    print(f"  Questions generated:  {total_questions}")
    print(f"  Time elapsed:         {elapsed:.1f}s ({elapsed/60:.1f}m)")
    print(f"  Dry run:              {dry_run}")
    print(f"{'=' * 50}")
