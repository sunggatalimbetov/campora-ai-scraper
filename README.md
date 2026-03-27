# Campora AI Scrapper

Telegram group message scraper with AI-powered importance filtering and vector embeddings. Feeds data into Supabase for the [Campora AI Helper](https://github.com/sunggatalimbetov/campora-ai-helper) bot.

## Features

- **Two-phase Pipeline** — batch scrape full history, then listen for new messages in real-time
- **AI Filtering** — GPT-4o-mini classifies messages by relevance (academic Q&A, announcements, deadlines vs. casual chat, spam)
- **Reply Chain Context** — resolves full conversation threads for better filtering decisions
- **Vector Embeddings** — OpenAI text-embedding-3-small (1536 dimensions) for semantic search
- **Resumable Scraping** — tracks progress per chat, resumes from last checkpoint on restart
- **Graceful Shutdown** — flushes buffered messages on SIGINT/SIGTERM

## Tech Stack

- **Python** with Telethon (Telegram MTProto userbot client)
- **OpenAI** — GPT-4o-mini for filtering, text-embedding-3-small for embeddings
- **Supabase** — PostgreSQL + pgvector
- **Docker** — multi-stage build for deployment

## Prerequisites

- Python 3.12+
- Telegram API credentials (`api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org))
- OpenAI API key
- Supabase project with pgvector enabled

## Environment Variables

Create a `.env` file in the project root:

```env
APP_API_ID=your-telegram-api-id
APP_API_HASH=your-telegram-api-hash
TELEGRAM_SESSION=your-telethon-session-string
OPENAI_API_KEY=your-openai-key
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your-service-role-key
```

Generate the session string (one-time, interactive):

```bash
python -m scripts.generate_session_string
```

## Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Configure target chats
# Edit chats.json with your chat IDs and metadata

# Run the scraper
python main.py
```

### Docker

```bash
docker build -t campora-ai-scrapper .
docker run --env-file .env campora-ai-scrapper
```

## Project Structure

```
src/
├── config/          # Environment variables
├── scraper/         # Core scraping pipeline
│   ├── fetch_channel_messages.py   # Telethon message fetching
│   ├── filter_messages_by_importance.py  # AI filtering with reply context
│   ├── build_reply_chains.py       # Reply thread resolution
│   ├── get_embedding.py            # Embedding generation
│   ├── save_messages_batch.py      # Supabase upsert
│   └── chat_state.py              # Scraping progress tracking
└── realtime/        # Real-time listener
    ├── main.py              # Two-phase orchestrator
    ├── initial_scrape.py    # Phase 1: batch history scrape
    ├── message_buffer.py    # Phase 2: buffer and flush
    └── pre_filter.py        # Local pre-filter (before AI)
scripts/             # Utility scripts
supabase/migrations/ # Database schema migrations
```

## How It Works

1. **Phase 1 (Batch)** — fetches full message history from configured Telegram groups, filters through AI, generates embeddings, and stores in Supabase
2. **Phase 2 (Real-time)** — listens for new messages, buffers them, and periodically flushes through the same AI filter → embed → store pipeline

Messages are deduplicated via composite key `(id, chat_id)` and scraping progress is checkpointed in the `chat_state` table.

## Database Migrations

```bash
supabase link --project-ref YOUR_PROJECT_REF
supabase db push
```

## Related Repos

- [campora-ai-helper](https://github.com/sunggatalimbetov/campora-ai-helper) — Telegram bot that searches the scraped data
- [campora-ai-dashboard](https://github.com/sunggatalimbetov/campora-ai-dashboard) — Analytics dashboard
