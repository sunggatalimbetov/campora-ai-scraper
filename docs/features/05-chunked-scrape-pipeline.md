# Chunked Scrape Pipeline with Checkpointing

## Problem
The NU Applicants scrape (~980K messages) takes 36+ hours because:
- All messages are fetched into memory at once before filtering
- AI filter runs batch_size=20 (41K API calls) with no checkpointing
- If the process crashes mid-filter, all progress is lost
- OpenAI 429 rate limits add ~8s delays per retry

## Solution
Process messages in chunks (e.g. 10K at a time) — fetch a chunk, filter it, save it, checkpoint, repeat. This makes the pipeline resumable, memory-efficient, and no slower than today.

## Changes

### 1. Refactor `initial_scrape.py` to process in chunks

**File:** `src/realtime/initial_scrape.py`

Instead of: fetch ALL → filter ALL → save ALL → checkpoint once

Do: loop { fetch chunk (10K) → filter chunk → save chunk → checkpoint }

```python
chunk_size = 10_000

while True:
    state = get_chat_state(chat_id)
    resume_from = state["last_message_id"] if state else None
    existing_ids = get_existing_message_ids(chat_id)

    messages = await fetch_channel_messages(chat_id, existing_ids, max_id=resume_from, limit=chunk_size)

    if not messages:
        upsert_chat_state(..., initial_scrape_done=True)
        break

    valuable = filter_messages_by_importance(messages, batch_size=50)

    if valuable:
        save_messages_batch(valuable, batch_size=10)

    # Checkpoint: save lowest message ID so next chunk starts below it
    lowest_id = min(msg["id"] for msg in messages)
    upsert_chat_state(chat_id, lowest_id, initial_scrape_done=False)
```

Key details:
- `fetch_channel_messages` already supports `max_id` (fetches messages with ID < max_id, i.e. older) and `limit`
- After each chunk, checkpoint `lowest_id` (not highest) because Telethon fetches newest-first
- `initial_scrape_done=False` until the final chunk returns empty
- On restart, it picks up from `last_message_id` in `chat_state`

### 2. Increase AI filter batch_size to 50

Change `filter_messages_by_importance(messages, batch_size=20)` → `batch_size=50`

This cuts API calls by 60% (200 calls per 10K chunk instead of 500). The prompt + 50 messages still fits well within gpt-4o-mini's context window (each message is truncated to 500 chars).

### 3. No changes needed to existing functions

- `fetch_channel_messages` — already supports `max_id` and `limit` params
- `filter_messages_by_importance` — already accepts `batch_size` param
- `save_messages_batch` — works on any list of messages
- `chat_state` — already has `get_chat_state` and `upsert_chat_state`
- `get_existing_message_ids` — works per chat_id

## Files to Modify
- `src/realtime/initial_scrape.py` — chunked loop with checkpointing (only file that changes)

## Verification
1. Reset chat_state for a test chat: set `initial_scrape_done=False`, `last_message_id=NULL`
2. Run `python3 main.py` — verify it processes in chunks of 10K
3. Kill the process mid-chunk, restart — verify it resumes from the last checkpoint
4. Verify memory usage stays flat (not growing with total message count)

## Notes
- After implementing, re-scrape any chat by setting `initial_scrape_done=False` in `chat_state`
- chunk_size=10K is a good default; can be tuned via parameter
