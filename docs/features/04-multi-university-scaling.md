# Feature: Multi-University Scaling

## Overview

Scale the bot from a single university (UNIME) to support multiple universities (e.g., University of Turin), introducing a multi-tenant architecture where each university is a tenant with its own data, search scope, and bot configuration.

## Current Limitations

- **Hardcoded chat IDs** in `data_scraper.py` (`CHAT_IDS = [-1002842855377]`)
- **No university scoping** in search — all messages are in one pool
- **Russian-only full-text search** hardcoded in migrations and tsvector config
- **University-specific terms** baked into AI prompts (VNЖ, ERSU, Esse3, Questura Messina)
- **Single-university evaluation** — 100 test questions are UNIME-specific
- **No university selection** in bot UX

## Architecture Changes

### 1. Data Layer — Add `university_id` Dimension

Add a `university_id` column to scope messages and a registry table for university configuration.

```sql
-- Add university column to messages
ALTER TABLE public.messages ADD COLUMN university_id TEXT NOT NULL DEFAULT 'unime';

-- Create a university registry
CREATE TABLE public.universities (
    id TEXT PRIMARY KEY,              -- 'unime', 'unito'
    name TEXT NOT NULL,               -- 'University of Messina'
    language TEXT NOT NULL,            -- 'russian', 'italian', 'english'
    chat_ids BIGINT[] NOT NULL,       -- Telegram chat IDs to scrape
    active BOOLEAN DEFAULT true
);

-- Index for fast filtering
CREATE INDEX idx_messages_university ON public.messages(university_id);

-- Backfill existing data
UPDATE public.messages SET university_id = 'unime';
```

**Why a single table, not separate tables per university?** At this scale (tens of thousands of messages, not millions), a single table with an index is simpler, avoids schema duplication, and makes cross-university search possible later.

### 2. Search — University-Scoped Hybrid Search

Update the `hybrid_search` RPC to accept a `filter_university_id` parameter:

```sql
CREATE OR REPLACE FUNCTION hybrid_search(
    query_text TEXT,
    query_embedding vector(1536),
    match_count INT,
    semantic_weight FLOAT,
    full_text_weight FLOAT,
    rrf_k INT DEFAULT 60,
    filter_university_id TEXT DEFAULT NULL  -- NEW
)
RETURNS TABLE(id BIGINT, chat_id BIGINT, text TEXT, link TEXT,
              similarity FLOAT, reply_to_message_id BIGINT)
AS $$
BEGIN
    -- Add WHERE university_id = filter_university_id
    -- to both the semantic and full-text subqueries
END;
$$;
```

In `message_search.py`, the `search_messages` method accepts a `university_id` parameter and passes it through to the RPC.

**Language-aware full-text search:** Store a `search_language` column in the `universities` table and use it during both ingestion (`to_tsvector(lang, ...)`) and search (`plainto_tsquery(lang, ...)`). This handles Torino using Italian while UNIME uses Russian.

### 3. Ingestion — Configuration-Driven Scraping

Replace hardcoded `CHAT_IDS` with a university config:

```python
# src/config/universities.py
UNIVERSITIES = {
    "unime": {
        "name": "University of Messina",
        "chat_ids": [-1002842855377],
        "language": "russian",
        "ts_config": "russian",
        "importance_prompt": "...",      # University-specific filtering criteria
    },
    "unito": {
        "name": "University of Turin",
        "chat_ids": [-100XXXXXXXXXX],
        "language": "russian",           # or "italian" depending on the community
        "ts_config": "russian",
        "importance_prompt": "...",
    },
}
```

The scraper becomes:

```python
async def scrape_university(university_id: str):
    config = UNIVERSITIES[university_id]
    for chat_id in config["chat_ids"]:
        messages = await fetch_messages(chat_id)
        # ... filter, embed, save with university_id
```

The AI importance filter prompt is also configurable per university — Torino may have different relevant topics.

### 4. Bot Interaction — University Context Resolution

Three approaches, in order of complexity:

**A. Separate bot instances (recommended to start)**
- Deploy one bot per university: `@unime_bot`, `@unito_bot`
- Each bot has a `UNIVERSITY_ID` env variable
- Zero ambiguity, no user confusion
- Easiest to manage and deploy

**B. Single bot with selection**
- `/start` asks the user to pick their university
- Store preference in a `user_preferences` table
- `/university` command to switch

**C. Single bot with auto-detection**
- Map group `chat_id` → `university_id` for group chats
- DMs still need explicit selection

Option A is recommended for MVP — operationally simpler and avoids cross-university confusion. Same codebase, different environment configs.

### 5. Answer Generation — University-Aware Prompts

The GPT-4o-mini prompt in `message_search.py` needs university context:

```python
UNIVERSITY_PROMPTS = {
    "unime": {
        "context": "University of Messina (UNIME), Erasmus students, mostly Russian-speaking",
        "terms": "VNЖ, ERSU, Esse3, CFU, Questura Messina, idoneo, assegnatario",
    },
    "unito": {
        "context": "University of Turin (UniTO), international students",
        "terms": "EDISU, MyUniTO, CLA, Questura Torino",
    },
}
```

### 6. Evaluation — Per-University Test Suites

For each new university:
1. Run `generate_eval_questions.py` scoped to that university's messages
2. Create `test_questions_unito.py` with Torino-specific questions
3. Run `evaluation_runner.py` per university to track quality independently

## Architecture Diagram

**Current (single-tenant):**
```
[UNIME Chat] → Scraper → [messages] → Search → [Bot] → User
```

**Proposed (multi-tenant):**
```
[UNIME Chat] → Scraper(unime) ─┐
                                ├→ [messages + university_id] → Search(uni) → Bot(uni) → User
[UniTO Chat] → Scraper(unito) ─┘
```

## Implementation Order

| Step | Change | Effort |
|------|--------|--------|
| 1 | Add `university_id` column + backfill existing data | Small |
| 2 | Create `universities` config module | Small |
| 3 | Update scraper to accept university config | Medium |
| 4 | Update `hybrid_search` RPC with university filter | Medium |
| 5 | Update `message_search.py` to pass `university_id` | Small |
| 6 | Add `UNIVERSITY_ID` env var to bot startup | Small |
| 7 | Update answer generation prompts per university | Small |
| 8 | Scrape Torino chat data | Medium |
| 9 | Generate Torino evaluation questions | Small |
| 10 | Deploy second bot instance | Small |

Steps 1–7 are pure refactoring with no behavior change for current users. Steps 8–10 are the actual Torino onboarding.

## What's NOT Needed (Yet)

- **Microservices** — The monolith is fine at this scale. Don't split into services until 10+ universities.
- **Separate databases** — One Supabase project with proper indexing handles this.
- **Message queues** — Scraping is batch, not real-time. A cron job per university is sufficient.
- **Multi-language embeddings** — `text-embedding-3-small` already handles Russian, Italian, and English well. No need for separate embedding models.

## Key Insight

This scales **linearly with configuration, not code changes**. Once the multi-tenant plumbing is in place, adding university #3, #4, etc. is just: add config, scrape data, deploy bot.
