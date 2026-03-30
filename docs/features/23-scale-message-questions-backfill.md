# Scale Message Questions Backfill

## Priority
P1 — High priority (scraper repo)

## Problem
The `message_questions` table (HyDE retrieval) covers 334 out of 231k messages (0.14%). NU Applicants alone has **204,455 messages** with near-zero question coverage. This causes `no_results` on critical queries like "Сколько нужно НУЕТ чтобы поступить в НУ" (failed 8 times). Bot satisfaction rate is 55.8%.

## Bugs Fixed
1. **Missing `chat_id` in inserts** — `message_questions` has `chat_id NOT NULL` with FK `(message_id, chat_id) → messages(id, chat_id)`. Old code only inserted `{message_id, question_text, embedding}`.
2. **Dedup by bare `message_id`** — Telegram IDs are only unique per chat. Old code used `set[int]` instead of `set[tuple[int, int]]`.

## Solution
Rewrite the backfill pipeline:
- **Groq Llama 3.1 8B** for question generation (fast, ~$3 for 204k messages)
- **OpenAI text-embedding-3-small** for embeddings (batch 2048/call)
- **Chunked processing** (1k messages per chunk)
- **Checkpoint/resume** to `backfill_progress.json`
- **Batch reply context** (1 DB query per chunk, not N+1)
- All inserts keyed by `(message_id, chat_id)`

## Processing Flow (per 1k-message chunk)
```
1. Fetch 1000 messages: WHERE chat_id=X AND id > cursor ORDER BY id
2. Batch-fetch reply parent texts (1 Supabase query)
3. Split into 40 batches of 25 messages
4. For each batch: rate-limited Groq call → {msg_id: [questions]}
5. Collect all questions (~2500 per chunk)
6. Batch embed via OpenAI (1-2 calls)
7. Batch insert into message_questions (chat_id included)
8. Save checkpoint
```

## Estimates (204k NU Applicants)

| Metric | Value |
|---|---|
| Groq API calls | ~8,179 (25 msgs/batch) |
| Groq cost | ~$2.95 |
| OpenAI embedding calls | ~250 (2048/batch) |
| OpenAI cost | ~$0.15 |
| Total cost | **~$3.10** |
| Wall time | **~12-15 min** |
| Questions generated | ~511k |

## Files

### New
- `scripts/backfill_questions/groq_client.py` — Groq client with token bucket rate limiter (800 RPM)
- `scripts/backfill_questions/batch_embeddings.py` — OpenAI batch embeddings (2048/call)
- `scripts/backfill_questions/reply_context.py` — Batch-fetch reply parent texts per chunk
- `scripts/backfill_questions/checkpoint.py` — Save/load progress to `backfill_progress.json`

### Modified
- `scripts/backfill_questions/backfill_questions.py` — Rewritten chunked orchestrator
- `scripts/backfill_questions/fetch_messages_without_questions.py` — Fixed composite key dedup, added `chat_id` filter
- `scripts/backfill_questions/main.py` — New CLI: `--chat-id`, `--chunk-size`, `--groq-batch-size`, `--resume`, `--dry-run`
- `src/config/settings.py` — Added `GROQ_API_KEY`
- `requirements.txt` / `pyproject.toml` — Added `groq`
- `.gitignore` — Added `backfill_progress.json`

## CLI Usage

```bash
# Dry run (100 messages, no DB writes)
python -m scripts.backfill_questions.main --chat-id 1002008115936 --limit 100 --dry-run

# Small live run (100 messages)
python -m scripts.backfill_questions.main --chat-id 1002008115936 --limit 100

# Full backfill
python -m scripts.backfill_questions.main --chat-id 1002008115936

# Resume after interruption
python -m scripts.backfill_questions.main --chat-id 1002008115936 --resume
```

## Verification
1. Dry run with 100 messages — verify Groq calls succeed, questions look reasonable
2. Small live run with 100 messages — check DB: `SELECT count(*) FROM message_questions WHERE chat_id = 1002008115936`
3. Resume test — kill mid-run, re-run with `--resume`, verify picks up from checkpoint
4. Full backfill — monitor progress, ~15 min
5. Bot test — ask "Сколько нужно НУЕТ чтобы поступить в НУ" → should return results

## Rollback
```sql
DELETE FROM message_questions WHERE chat_id = 1002008115936;
```
