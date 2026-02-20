# Feature: Reply Chain Context & Codebase Refactoring

## Overview

Two major changes in this update:

1. **Reply chain context for the data scraper** — The AI importance filter now sees full conversation threads instead of isolated messages, preserving valuable reply-answer pairs in the database.
2. **Codebase refactoring** — All monolithic scripts and services were split into one-function-per-file packages for better maintainability.

## Problem Statement

### Missing Replies in Search Results

When users asked the bot a question like "Когда начинается второй семестр?", the bot found the right question messages in the database but returned **no answers**. Investigation revealed:

- The database had **0 reply messages** linked to the found questions
- Root cause: the scraping pipeline was filtering out reply messages at two stages:
  1. **`should_process_message`** — Hard-coded filters dropped messages shorter than 16 characters, single-word messages, and emoji-heavy messages. Short replies like "2 марта" (8 chars) or "Понедельник" were silently discarded.
  2. **AI importance filter** — Evaluated each message in isolation with only `{id, text}`. A reply like "March 2nd" looks meaningless without the question it answers, so the AI filtered it out.

### Monolithic Code Structure

Scripts like `message_search.py` (552 lines), `data_scraper.py` (290 lines), and `backfill_questions.py` (198 lines) were single files containing multiple functions, making navigation and maintenance difficult.

## Solution

### 1. Reply Chain Algorithm (`build_reply_chains.py`)

New function that resolves reply chains by walking up `reply_to_message_id` recursively:

```
Message 102 ("Thanks!")
  └─ replies to → Message 101 ("March 2nd")
       └─ replies to → Message 100 ("When does semester start?")

Chain for msg 102: [101, 100]
Chain for msg 101: [100]
Chain for msg 100: []
```

- Looks up parent messages in the current batch first, falls back to database
- Capped at 5 levels of depth to prevent infinite loops
- Caches DB lookups to avoid repeated queries

### 2. Updated AI Importance Filter (`filter_messages_by_importance.py`)

Three changes:

- **Reply context in prompt**: Each message sent to GPT now includes `reply_context` — the text of its parent chain. The AI sees the full conversation thread when judging value.
- **Updated prompt**: Explicitly instructs the AI to keep replies that answer valuable questions, even if the reply text is short.
- **Auto-expand reply chains**: After AI filtering, `_expand_reply_chains()` ensures that if any message in a thread is kept, its parents AND direct replies are also kept.

### 3. Removed `should_process_message` Filter

The hard-coded text quality filter was removed from `fetch_channel_messages.py`. Now the only pre-filter is `msg.text and msg.text.strip()` (message has any text at all). All importance decisions are made by the AI filter with full context.

### 4. Fixed `_merge_results` in Search

Previously, reply fetching in `_merge_results` only ran for messages with `match_source == "question"`. Messages from hybrid search that weren't overridden by question results had `match_source: null` and were skipped. Now reply fetching runs for **all** merged results.

### 5. Codebase Refactoring

All monolithic files were split into packages following the convention: **one file per public function, private/internal functions stay with their caller**.

| Before | After |
|---|---|
| `src/services/message_search.py` (552 lines) | `src/services/message_search/` (9 files) |
| `scripts/backfill_questions.py` (198 lines) | `scripts/backfill_questions/` (4 files) |
| `scripts/generate_eval_questions.py` (261 lines) | `scripts/generate_eval_questions/` (6 files) |
| `scripts/update_reply_ids.py` (119 lines) | `scripts/update_reply_ids/` (4 files) |
| `src/services/data_scraper.py` (290 lines) | `scripts/data_scraper/` (8 files) |
| `tests/evaluation/evaluation_runner.py` (231 lines) | `tests/evaluation/evaluation_runner/` (4 files) |

Each package has an `__init__.py` with re-exports, so existing imports like `from src.services.message_search import search_messages` continue working unchanged.

Additional cleanup:
- Shared clients (`supabase`, `client_oa`) moved to `_clients.py` instead of being duplicated in every file
- All imports standardized to `from src.config.settings import ...`
- Indentation converted to tabs throughout
- Removed Black from pre-commit hooks (incompatible with tabs)
- Disabled flake8 W191/E101 (tab indentation rules)

## Data Safety

Re-running the scraper after these changes:
- **No duplicates**: `fetch_channel_messages` checks `existing_ids` from the database and skips any message already saved
- **No drops**: `save_messages_batch` only inserts, never modifies or deletes existing rows
- **New messages picked up**: Messages previously dropped by `should_process_message` or the old AI filter were never saved, so they appear as "new" and get a second chance through the improved pipeline

## Files Changed

### New Files
- `scripts/data_scraper/build_reply_chains.py` — Reply chain resolution algorithm

### Modified Files
- `scripts/data_scraper/filter_messages_by_importance.py` — Reply context in AI prompt + chain expansion
- `scripts/data_scraper/fetch_channel_messages.py` — Removed `should_process_message` filter
- `src/services/message_search/search_messages.py` — Reply fetching for all merged results
- `.flake8` — Disabled W191, E101
- `.pre-commit-config.yaml` — Removed Black hook

### Refactored (file → package)
- `src/services/message_search.py` → `src/services/message_search/`
- `scripts/backfill_questions.py` → `scripts/backfill_questions/`
- `scripts/generate_eval_questions.py` → `scripts/generate_eval_questions/`
- `scripts/update_reply_ids.py` → `scripts/update_reply_ids/`
- `src/services/data_scraper.py` → `scripts/data_scraper/`
- `tests/evaluation/evaluation_runner.py` → `tests/evaluation/evaluation_runner/`
