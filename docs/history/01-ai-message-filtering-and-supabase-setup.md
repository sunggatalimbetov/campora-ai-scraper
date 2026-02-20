# 01 – AI message filtering and Supabase setup

**Date:** 2026-02-13

## Summary

We added AI-based importance filtering to the Telegram data scraper and set up the database schema so the scraper and bot can run against Supabase.

---

## 1. AI message filtering in the data scraper

**Problem:** The scraper stored every message that passed basic quality checks, including spam, casual chat, and off-topic content.

**Solution:** An AI filter step was added so only “valuable” messages are embedded and saved.

### Pipeline change

- **Before:** Fetch → basic filter → embeddings → save.
- **After:** Fetch → basic filter → **AI importance filter (batches of 20)** → embeddings → save.

### Implementation

- **`filter_messages_by_importance(messages, batch_size=20)`** in `src/services/data_scraper.py`:
    - Sends each batch of 20 messages to **GPT-4o-mini** with a fixed prompt.
    - Model returns a JSON array of message IDs to keep.
    - Only those messages are passed on for embedding and DB insert.
    - On API/parse errors, the whole batch is kept (fail-open).
    - Rate limiting: 1 second pause between AI batches.

- **`_parse_valuable_ids()`** parses the model response and intersects with the current batch IDs so only valid IDs are kept.

- **`scrape_channel()`** runs the AI filter after fetching and before `save_messages_batch()`. If no messages are valuable, it exits without calling the DB.

### Keep vs filter-out criteria

**Keep:** Announcements and deadlines; academic Q&A; resources, links, study materials, exams; official info from professors/admins; documents (Visa, Residence Permit); Erasmus and transfer programs; course registration and enrollment; campus facilities and services; scholarships and financial aid; internships and job opportunities.

**Filter out:** Renting; bank transfers; casual chat; toxic/argumentative; spam, memes, off-topic; single-word replies; selling/buying; food/restaurants; social events (non-academic); ride sharing; venting; gaming/entertainment.

### Logging

- Per batch: `AI filter batch X/Y: kept A/B messages`.
- Once after filtering: `AI filter: N messages -> M valuable (K filtered out)`.

---

## 2. Supabase schema and migrations

**Problem:** The `messages` table and `match_messages` RPC did not exist, so the scraper and search failed with “Could not find the table 'public.messages'”.

**Solution:** SQL migrations were added and documented for both manual runs and Supabase CLI.

### Files added/updated

- **`supabase/migrations/20260213210000_create_messages_table.sql`**
    - `CREATE EXTENSION IF NOT EXISTS vector;`
    - `public.messages`: `id` (BIGINT PK), `chat_id`, `author`, `text`, `link`, `embedding vector(1536)`, `reply_to_message_id`.
    - `public.match_messages(query_embedding, match_count)` RPC used by `message_search.search_messages()`.

- **`sql/001_messages_table_and_match.sql`** – same schema for running manually in the Supabase SQL Editor.

- **`sql/README.md`** – how to apply migrations:
    - **CLI:** `supabase login` → `supabase link --project-ref <ref>` → `supabase db push`.
    - **Dashboard:** paste `sql/001_messages_table_and_match.sql` into SQL Editor and run.

- **`supabase/`** – `supabase init` was run so the project has `config.toml` and is ready for `supabase link` and `supabase db push`.

---

## 3. Operational notes documented

- **Running the scraper:** From project root, `python -m src.services.data_scraper` (or `PYTHONPATH=. python src/services/data_scraper.py`). Configure channel and optional `MAX_ID` / `LIMIT` in `main()`.

- **Preventing sleep during long runs:** Use `caffeinate -i python -m src.services.data_scraper`, or set “Turn display off when inactive” to Never in System Settings → Lock Screen (especially when on power adapter).

- **Resuming after stop:** Use the printed `max_id` as `MAX_ID` in `main()` for the next run so the scraper continues from the last saved message.
