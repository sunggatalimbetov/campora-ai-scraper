# CLAUDE.md — Vectir AI Scrapper

## What is this?
Telegram message scraper that connects to university group chats as a userbot (Telethon), filters messages for importance using GPT-4o-mini, generates embeddings, and stores everything in Supabase for search. Part of the Vectir AI system (3 repos: helper, scrapper, dashboard).

## Architecture
```
[Telegram Groups] → vectir-ai-scrapper (this repo) → [Supabase DB]
                     Phase 1: batch scrape history
                     Phase 2: real-time listener
```

## Tech Stack
- Python 3.9, Telethon (MTProto userbot, not bot API)
- OpenAI GPT-4o-mini (importance filtering)
- OpenAI text-embedding-3-small (1536 dim) for embeddings
- Supabase (PostgreSQL + pgvector)
- Docker support

## Key Files
- `main.py` — entry point, chat IDs list
- `src/realtime/main.py` — two-phase orchestrator (batch scrape → live listener)
- `src/realtime/initial_scrape.py` — Phase 1: full history scrape
- `src/realtime/message_buffer.py` — Phase 2: buffer and flush new messages
- `src/scraper/filter_messages_by_importance.py` — GPT-4o-mini AI filter with reply chain context
- `src/scraper/save_messages_batch.py` — embedding generation + Supabase upsert
- `src/scraper/build_reply_chains.py` — reply thread resolution
- `src/scraper/fetch_channel_messages.py` — Telethon message fetching
- `src/scraper/chat_state.py` — resumable scraping state
- `src/config/settings.py` — env vars and configuration
- `supabase/migrations/` — database migrations

## What NOT to change
- Reply chain building logic
- Batch processing flow (fetch → filter → embed → save)
- Telethon session handling
- OpenAI API call structure for filtering
- Project directory structure

## Coding Conventions
- Conventional commits: `feat:`, `fix:`, `refactor:`
- Each commit small and focused (one logical change)
- Each commit has summary line + brief description body
- New features get their own branch
- Python: follow existing code style

## Current State
- Chat IDs hardcoded in main.py (needs config file)
- Filter prompt has some Messina-specific examples (needs generalization)
- messages table has no created_at column
- Phase 1 (batch) and Phase 2 (real-time) both work
- Graceful shutdown flushes buffer on SIGINT/SIGTERM
- chat_state table enables resumable scraping

## Important Details
- Telethon session file: `session.session` (DO NOT delete or regenerate)
- Rate limiting: 1s pause between Supabase batches
- Filter processes messages in batches of 20
- Embedding dimension: 1536 (text-embedding-3-small)
- Messages are upserted on composite key (id, chat_id)
- opted_out_users table should be checked before indexing (not yet implemented)
