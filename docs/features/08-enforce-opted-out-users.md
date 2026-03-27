# Enforce Opted-Out Users Filtering

## Priority
P1 — Pre-launch blocker

## Problem
The `opted_out_users` table is mentioned in CLAUDE.md as a planned privacy feature, but it doesn't exist yet and no code checks it. If a user opts out, their messages are still scraped, embedded, and searchable.

## Solution
1. Create the `opted_out_users` table via a new Supabase migration
2. Add a Python module `src/scraper/opted_out_users.py` that queries the table
3. Filter out opted-out authors in both pipeline entry points (initial scrape + real-time buffer flush), before the AI importance filter runs

## Schema

```sql
CREATE TABLE public.opted_out_users (
    user_id     BIGINT NOT NULL,
    chat_id     BIGINT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, chat_id)
);
```

Composite PK allows a user to opt out per-group. Index on `chat_id` for fast per-chat lookups.

## Changes

### Scrapper repo
- `supabase/migrations/YYYYMMDD_create_opted_out_users.sql` (new)
- `src/scraper/opted_out_users.py` (new) — `get_opted_out_user_ids(chat_id) -> Set[int]`
- `src/scraper/__init__.py` — export new module
- `src/realtime/initial_scrape.py` — call `get_opted_out_user_ids()` before `filter_messages_by_importance()`
- `src/realtime/message_buffer.py` — same filtering in `_flush_chat()`

### Helper repo (future)
- Add `/optout` command handler so users can add themselves to the table
- Potentially delete existing messages from opted-out users (backfill cleanup)

## Verification
1. Insert a test row into `opted_out_users`
2. Run the scraper — messages from that user should be excluded from saved output
3. Remove the row — messages should appear again on next scrape
