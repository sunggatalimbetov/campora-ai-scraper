# Date-Aware Responses

## Priority
P1 — High priority (helper repo)

## Problem
The bot retrieves old messages (e.g., from 2023-2024) that contain temporal phrases like "завтра", "следующая неделя", "в мае", and presents them as current facts. Users dislike these responses because the dates are stale.

Observed failures:
- "Когда офферы?" → "Офферы будут завтра" (sourced from a 2023 message) → disliked
- "Когда офферы?" → "Офферы ожидаются на следующей неделе" → disliked
- "Когда офферы?" → "Офферы в конце мая - начале июня" → disliked

## Root Cause
The `created_at` field is already stored on messages and returned by all search RPCs (`match_messages`, `hybrid_search`, `match_messages_and_questions`). However, the helper repo's answer generation prompt ignores it — the LLM sees the message text with no date context and confidently presents relative dates as current.

## Solution

### 1. Pass `created_at` to the LLM prompt
When building the context for the answer generation prompt, include the message date alongside each source:

```
Source [1] (posted 2023-05-10): "Офферы будут завтра"
Source [2] (posted 2024-04-22): "Офферы в мае"
```

### 2. Add system prompt instruction
Add to the system prompt:

```
When answering time-sensitive questions (deadlines, dates, offer releases, exam schedules):
- Always note the date of the source message
- If the source is older than 6 months, add: "Note: this info is from [date] and may not reflect current deadlines"
- Never state a future date as fact if the source message is from a previous year
- If you can't find a current-year source for a time-sensitive question, say so explicitly
```

### 3. Detect time-sensitive queries (optional enhancement)
Classify queries before answering:
- Time-sensitive keywords: "когда", "when", "deadline", "оффер", "дедлайн", "дата", "число", "срок"
- Apply stricter disclaimers for these query types

## Changes
- **Helper repo:** `src/services/message_search/generate_answer.py` — pass `created_at` per source into prompt context
- **Helper repo:** `src/prompts/` or equivalent — update system prompt with date-awareness instructions

## Verification
1. Ask "когда офферы?" — response should include source dates and a staleness caveat if sources are >6 months old
2. Ask "когда экзамен по нует?" — same behavior
3. Check that non-time-sensitive questions (e.g., "что такое фаунд?") are not affected
