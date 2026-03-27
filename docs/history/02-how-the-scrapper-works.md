# 02 – How the scrapper works

**Date:** 2026-02-20

## Summary

The scrapper is a long-running Python process that connects to Telegram via Telethon, scrapes university group chat history, filters messages with AI, generates embeddings, and stores everything in Supabase. It operates in two phases: an initial one-shot batch scrape for new groups, then a continuous real-time event listener that buffers incoming messages and flushes them through the same pipeline.

---

## Architecture overview

```
main.py
  └─ src/realtime/main.py  run(chat_ids)
       ├─ Phase 1: initial_scrape() per chat
       │    └─ Existing pipeline: fetch → AI filter → save with embeddings
       └─ Phase 2: Telethon NewMessage event handler
            └─ pre-filter → MessageBuffer → flush → same pipeline
```

**Two phases, one pipeline.** Both the batch scraper and the real-time listener call the same underlying functions in `src/scraper/`.

---

## Phase 1: Initial batch scrape

Runs once per chat group when it has never been scraped before.

**Entry point:** `src/realtime/initial_scrape.py` → `initial_scrape(chat_id)`

### How it decides whether to run

1. Queries the `chat_state` table in Supabase for the given `chat_id`.
2. If no row exists, or `initial_scrape_done` is `false`, runs the full batch scrape.
3. If `initial_scrape_done` is `true`, skips immediately.

If a previous run was interrupted, it resumes from `chat_state.last_message_id` (passed as `max_id` to Telethon's `iter_messages`).

### Pipeline steps

1. `**get_existing_message_ids(chat_id)`** — Queries all message IDs already in the `messages` table for this chat (batched reads of 1000). Returns a `Set[int]` used for dedup.
2. `**fetch_channel_messages(chat_id, existing_ids, max_id, limit)**` — Iterates through the chat history using `client.iter_messages()`. Skips messages whose ID is in `existing_ids`. Only keeps messages that have non-empty text. Returns a list of message dicts:
  ```
    {"id", "chat_id", "author", "text", "link", "reply_to_message_id"}
  ```
    The `link` is built as `https://t.me/c/{raw_id}/{msg.id}` where `raw_id` is the chat ID without the `-100` prefix.
3. `**filter_messages_by_importance(messages, batch_size=20)**` — AI-based filtering using GPT-4o-mini:
  - Builds reply chains first (`build_reply_chains`) — walks up `reply_to_message_id` recursively (max 5 levels), checks the current batch then falls back to DB lookups.
    - Sends batches of 20 messages to GPT-4o-mini with a prompt that classifies each message as valuable or not. Reply context (parent chain text) is included so short replies that answer important questions are preserved.
    - Parses the response (JSON array of kept IDs), then expands the kept set to include full reply chains (ancestors + direct replies).
    - Fail-open: on any API or parse error, the entire batch is kept.
    - 1 second pause between batches for rate limiting.
4. `**save_messages_batch(valuable, batch_size=10)**` — Saves messages in batches of 10:
  - Generates a 1536-dim embedding per message using OpenAI `text-embedding-3-small`.
    - Upserts into the `messages` table with composite PK `(id, chat_id)`.
    - On batch failure, falls back to individual upserts.
    - 1 second pause between batches.
5. `**upsert_chat_state(chat_id, highest_id, initial_scrape_done=True)**` — Persists the highest saved message ID and marks the chat as fully scraped.

---

## Phase 2: Real-time event listener

After all initial scrapes complete, the process stays alive and listens for new messages.

**Entry point:** `src/realtime/main.py` → `run(chat_ids)` (second half)

### Event handler

A Telethon `events.NewMessage` handler fires for every new message in the monitored chats. Before buffering, two cheap local checks run:

1. **Text check** — `msg.text and msg.text.strip()` — skips media-only messages.
2. **Pre-filter** (`src/realtime/pre_filter.py`) — `should_buffer(text)` rejects:
  - Messages shorter than 3 characters
    - Single reactions like `да`, `нет`, `ок`, `спс`, emoji
    - Bare mentions (`@username`)
    - Just `+`

Messages that pass are added to the `MessageBuffer`.

### MessageBuffer

`src/realtime/message_buffer.py` — an async-safe in-memory buffer with per-chat message lists.

- `**add(chat_id, message)`** — appends the message to `buffer[chat_id]` under an `asyncio.Lock`. If the buffer for that chat reaches 1000 messages, triggers an immediate flush.
- `**_flush_chat(chat_id)**` — takes all messages out of the buffer for that chat and runs them through the same pipeline as Phase 1: `get_existing_message_ids` → `filter_messages_by_importance` → `save_messages_batch` → `upsert_chat_state`.
- `**periodic_flush()**` — background `asyncio` task that flushes all non-empty buffers every 7 days (604800 seconds). Ensures low-traffic chats eventually get processed even if they never hit the 1000-message threshold.
- `**flush_all()**` — flushes every chat buffer. Called by the periodic timer and by the signal handlers on shutdown.

### Graceful shutdown

`src/realtime/signal_handlers.py` registers handlers for `SIGINT` (Ctrl+C) and `SIGTERM` (docker stop) using `loop.add_signal_handler`. On signal:

1. Calls `buffer.flush_all()` — processes and saves all buffered messages.
2. Updates `chat_state.last_message_id` for each flushed chat.
3. Disconnects the Telethon client, which causes `run_until_disconnected()` to return and the process to exit.

On hard kill (`kill -9` / power loss), `chat_state` is at most one flush behind since it's updated after every `save_messages_batch`.

---

## Database

### Tables

`**messages**` — composite PK `(id, chat_id)`:


| Column                | Type         | Notes                                          |
| --------------------- | ------------ | ---------------------------------------------- |
| `id`                  | BIGINT       | Telegram message ID (unique within a chat)     |
| `chat_id`             | BIGINT       | Absolute Telegram chat ID                      |
| `author`              | BIGINT       | Sender user ID                                 |
| `text`                | TEXT         | Message text                                   |
| `link`                | TEXT         | `https://t.me/c/{raw_id}/{msg_id}`             |
| `embedding`           | vector(1536) | OpenAI text-embedding-3-small                  |
| `reply_to_message_id` | BIGINT       | Parent message ID (nullable)                   |
| `text_search`         | tsvector     | Auto-populated Russian full-text search column |


`**chat_state**` — PK `chat_id`:


| Column                | Type        | Notes                                              |
| --------------------- | ----------- | -------------------------------------------------- |
| `chat_id`             | BIGINT      | Absolute Telegram chat ID                          |
| `last_message_id`     | BIGINT      | Highest message ID successfully saved              |
| `initial_scrape_done` | BOOLEAN     | True after the first full-history scrape completes |
| `updated_at`          | TIMESTAMPTZ | Auto-updated on every write                        |


`**message_questions**` — generated hypothetical questions per message (populated by a separate backfill script in `scripts/backfill_questions/`).

---

## File structure

```
campora-ai-scrapper/
├── main.py                          # Entry point: defines CHAT_IDS, calls run()
├── src/
│   ├── config/
│   │   └── settings.py              # Env vars: API keys, Supabase, Telegram session
│   ├── scraper/                     # Core pipeline (shared by both phases)
│   │   ├── fetch_channel_messages.py    # Telethon client + iter_messages
│   │   ├── get_existing_message_ids.py  # Dedup query against Supabase
│   │   ├── build_reply_chains.py        # Reply chain resolution (batch + DB)
│   │   ├── filter_messages_by_importance.py  # GPT-4o-mini importance filter
│   │   ├── save_messages_batch.py       # Embedding generation + DB upsert
│   │   ├── get_embedding.py             # OpenAI text-embedding-3-small wrapper
│   │   ├── chat_state.py               # get_chat_state / upsert_chat_state
│   │   └── scrape_channel.py           # Legacy one-shot orchestration (unused)
│   └── realtime/                    # Two-phase architecture
│       ├── main.py                  # run(): Phase 1 + Phase 2
│       ├── initial_scrape.py        # Phase 1: batch scrape for new groups
│       ├── message_buffer.py        # Phase 2: MessageBuffer class
│       ├── pre_filter.py            # Phase 2: should_buffer() noise filter
│       └── signal_handlers.py       # SIGINT/SIGTERM → flush + disconnect
├── scripts/
│   ├── generate_session_string.py   # One-time utility to get TELEGRAM_SESSION
│   ├── backfill_questions/          # Generate hypothetical questions for messages
│   ├── generate_eval_questions/     # Generate evaluation test questions
│   └── update_reply_ids/           # Backfill reply relationships
├── supabase/
│   └── migrations/                  # SQL migrations (apply with supabase db push)
├── Dockerfile                       # python:3.12-slim, runs main.py
└── requirements.txt                 # python-dotenv, openai, supabase, telethon
```

---

## Configuration

All config comes from environment variables (loaded by `python-dotenv` from `.env`):


| Variable               | Used by                                                         |
| ---------------------- | --------------------------------------------------------------- |
| `APP_API_ID`           | Telethon client (Telegram API)                                  |
| `APP_API_HASH`         | Telethon client (Telegram API)                                  |
| `TELEGRAM_SESSION`     | Telethon StringSession (no file-based session needed in Docker) |
| `OPENAI_API_KEY`       | Embedding generation + AI importance filter                     |
| `SUPABASE_URL`         | All Supabase queries                                            |
| `SUPABASE_SERVICE_KEY` | All Supabase queries                                            |


`CHAT_IDS` is hardcoded in `main.py`.

---

## Running

**Local:**

```
python main.py
```

**Docker:**

```
docker build -t campora-scrapper .
docker run --env-file .env campora-scrapper
```

**Generating a session string** (one-time, local only):

```
python -m scripts.generate_session_string
```

Authenticate interactively, then copy the printed string into `TELEGRAM_SESSION`.

---

## Cost model

Processing messages in batches of 1000 instead of one at a time reduces AI costs by 10-20x:


| Approach                   | AI calls per 1000 messages | Tokens (approx) |
| -------------------------- | -------------------------- | --------------- |
| Per-message                | 1000                       | ~500K           |
| Batched (50 batches of 20) | 50                         | ~50K            |


The AI filter also works better in batches because it sees conversation context (reply chains, conversation flow).