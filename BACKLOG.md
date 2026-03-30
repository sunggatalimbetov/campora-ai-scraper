# Backlog

Current implementation backlog for `main` as of 2026-03-29.

This file is the working priority list for the scraper repo. Detailed design notes live in `docs/features/`, but this file should reflect what is actually next.

## Next Up

### P1 — Pre-launch blocker

#### 1. Enforce `opted_out_users`
- Create the `opted_out_users` table via Supabase migration.
- Add `src/scraper/opted_out_users.py` with `get_opted_out_user_ids(chat_id)`.
- Filter opted-out authors before AI filtering in:
  - `src/realtime/initial_scrape.py`
  - `src/realtime/message_buffer.py`
- Follow-up decision: whether to delete already-indexed messages for opted-out users.

### P2 — Reliability

#### 2. Add retry logic with exponential backoff
- Add retries around OpenAI embedding generation.
- Add retries around the AI importance filter call.
- Add retries around Supabase upserts.
- Suggested implementation doc: `docs/features/11-retry-logic-with-backoff.md`

#### 3. Reconnect if Telegram disconnects
- `client.run_until_disconnected()` currently exits the process with no recovery.
- Add reconnect loop or at least explicit alerting and controlled restart behavior.

#### 4. Share a single Supabase client
- `chat_state.py`, `build_reply_chains.py`, `get_existing_message_ids.py`, `save_messages_batch.py`, and `opted_out_users.py` each create a client at import time.
- Replace this with one shared client module.

#### 4a. Add opt-back-in path for opted-out users
- Currently opting back in requires a manual `DELETE` from `opted_out_users`.
- Add a helper or endpoint so users can reverse their opt-out.

#### 5. Remove event-loop blocking from the ingestion path
- `time.sleep(1)` in `filter_messages_by_importance.py` blocks the async runtime.
- Sync Supabase lookups in `build_reply_chains._lookup_message()` block reply-chain resolution.
- `MessageBuffer` currently holds its lock while doing DB and OpenAI work, which can stall ingestion for all chats.

#### 6. Complete Telegram env var validation
- `APP_API_ID`, `APP_API_HASH`, and `TELEGRAM_SESSION` still fall back to `0` or empty strings.
- Make startup validation fail fast for the required Telegram client settings too.

### P3 — Maintainability

#### 7. Replace `print()` calls with structured logging
- Move scraper and realtime pipeline output to `logging`.
- Keep log messages operationally useful: chat id, batch size, retry count, flush timing, and failure context.
- Suggested implementation doc: `docs/features/10-replace-print-with-logging.md`

#### 8. Extract magic numbers into config/constants
- Centralize batch sizes, flush thresholds, flush intervals, retry delays, and reply-chain depth.
- Suggested implementation doc: `docs/features/16-extract-magic-numbers.md`

### P4 — Quality

#### 9. Add test coverage
- Start with unit tests for pure logic:
  - `src/realtime/pre_filter.py`
  - `_parse_valuable_ids()` and `_expand_reply_chains()`
  - reply-chain resolution helpers
- Then add integration tests around message buffering and save flow.
- Suggested implementation doc: `docs/features/15-add-tests.md`

## Completed Recently

### Small cleanup fixes
- Fixed `last_message_id` checkpointing to use the highest fetched message id.
- Added fast-fail validation for required OpenAI and Supabase env vars.
- Removed redundant `load_dotenv()` in `save_messages_batch.py`.
- Fixed invalid `set[Any]()` usage in `get_existing_message_ids.py`.
- Extracted Telegram `t.me/c/...` link generation into `src/scraper/telegram_links.py`.
- Generalized the AI filter prompt so it is not tied to one university context.

### Docs cleanup
- Removed outdated feature docs that no longer matched the current repo state.

## Notes

- `docs/features/12-env-var-validation.md` is effectively done for the current required OpenAI and Supabase vars.
- The older local code-review backlog items have been folded into the priorities above so this file can stay concise and current.
