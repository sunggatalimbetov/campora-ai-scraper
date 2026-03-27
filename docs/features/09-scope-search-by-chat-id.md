# Scope Search Results by chat_id

## Priority
P1 — Pre-launch blocker

## Problem
Search RPCs (`match_messages`, `hybrid_search`, `match_messages_and_questions`) return results from ALL groups globally. When a user asks in NU Applicants, they get Messina results mixed in.

## Solution
Add an optional `target_chat_id BIGINT DEFAULT NULL` parameter to all three RPCs. When NULL, search all groups (current behavior for DMs). When set, filter to that group only.

## Current Flow
```
Handler (has chat_id) → search_messages(query) → hybrid_search(query) → Supabase RPC (no chat filter)
```

## Target Flow
```
Handler (has chat_id) → search_messages(query, chat_id) → hybrid_search(query, chat_id) → Supabase RPC (WHERE chat_id = target)
```

## Changes

### 1. SQL Migration (scraper repo)
**File:** `supabase/migrations/YYYYMMDD_add_chat_id_filter_to_rpcs.sql`

Must `DROP FUNCTION` before recreating (PG can't change signatures with CREATE OR REPLACE).

**match_messages:** Add `AND (target_chat_id IS NULL OR m.chat_id = target_chat_id)` to WHERE clause.

**hybrid_search:** Add the same filter to both `semantic_search` and `full_text_search` CTEs.

**match_messages_and_questions:** Add the filter to both `message_matches` and `question_matches` CTEs.

### 2. Thread chat_id through Python search functions (helper repo)

**`src/services/message_search/search_messages.py`**
- Add `chat_id: Optional[int] = None` parameter to `search_messages()`
- Pass it to `search_messages_hybrid()` and `search_messages_by_questions()`

**`src/services/message_search/search_messages_hybrid.py`**
- Add `chat_id: Optional[int] = None` parameter
- Pass `"target_chat_id": chat_id` to the `hybrid_search` RPC call
- Fallback call to `search_messages_semantic_only` also passes `chat_id`

**`src/services/message_search/search_messages_semantic_only.py`**
- Add `chat_id: Optional[int] = None` parameter
- Pass `"target_chat_id": chat_id` to the `match_messages` RPC call

**`src/services/message_search/search_messages_by_questions.py`**
- Add `chat_id: Optional[int] = None` parameter
- Pass `"target_chat_id": chat_id` to the `match_messages_and_questions` RPC call

### 3. Pass chat_id from handlers (helper repo)

**`src/handlers/commands.py`** (`/ask` command)
- Already extracts `chat_id = update.effective_chat.id`
- Pass it to `search_messages(search_query, chat_id=chat_id)`

**`src/handlers/messages.py`** (DM handler)
- In DMs, `chat_id` is the user's private chat — NOT a group. Pass `chat_id=None` to search all groups.

## Verification
1. Push migration: `supabase db push`
2. Test in a group: `/ask` should only return messages from that group's chat_id
3. Test in DMs: should still return results from all groups
4. Verify hybrid search, semantic-only fallback, and question search all respect the filter
