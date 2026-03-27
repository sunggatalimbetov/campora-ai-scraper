# Response Time Breakdown Logging

## Priority
P5 — Future feature (helper repo)

## Problem
When bot responses are slow, we can't tell which stage is the bottleneck — embedding generation, vector search, or LLM answer generation. The `bot_interactions` table only stores total `response_time_ms`.

## Solution
Track per-stage latency in the answer pipeline and store breakdowns in `bot_interactions` or a new `response_timings` table.

### Stages to measure
1. Query embedding generation (OpenAI)
2. Hybrid search (Supabase RPC)
3. Question-based search (Supabase RPC)
4. Answer generation (LLM chat completion)
5. Total end-to-end

### Approach
- Use `time.perf_counter()` around each stage
- Store as JSON in a new `timing_breakdown` column on `bot_interactions`
- Example: `{"embed_ms": 120, "search_ms": 340, "llm_ms": 1800, "total_ms": 2300}`

## Changes
- **Helper repo:** `src/services/message_search/` — wrap each stage with timing
- **Helper repo:** `src/handlers/` — collect and store timings
- **Scrapper repo (optional):** new migration to add `timing_breakdown JSONB` to `bot_interactions`

## Verification
1. Send a query to the bot
2. Check `bot_interactions` — `timing_breakdown` should show per-stage latency
3. Verify sum of stages ≈ total response time
