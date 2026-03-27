# Add Retry Logic with Exponential Backoff

## Priority
P2 — Reliability

## Problem
Single failures in OpenAI or Supabase API calls cause messages to be silently dropped or kept unfiltered. No retry logic exists — the AI filter catches exceptions and keeps all messages, and embedding failures skip the message entirely.

## Solution
Add `tenacity` library for retry with exponential backoff on all external API calls:
- OpenAI embedding generation (`get_embedding`)
- OpenAI chat completion for AI filter (`filter_messages_by_importance`)
- Supabase batch upsert (`save_messages_batch`)

Configuration: `@retry(wait=wait_exponential(min=1, max=30), stop=stop_after_attempt(3))`

## Files to Change
- `requirements.txt` — add `tenacity`
- `src/scraper/get_embedding.py` — decorate `get_embedding()` with `@retry`
- `src/scraper/filter_messages_by_importance.py` — extract API call to `_call_ai_filter()`, decorate with `@retry`
- `src/scraper/save_messages_batch.py` — extract upsert to `_upsert_batch()`, decorate with `@retry`

## Verification
1. Temporarily break OpenAI API key — should retry 3 times before failing
2. Check logs for retry attempts
3. Normal operation should be unaffected (retries only trigger on exceptions)
