# Clarification Behavior for Vague Queries

## Priority
P5 — Future feature (helper repo)

## Problem
When a user sends a vague query like "when?" or "what about documents?", the bot guesses and often returns irrelevant results. This erodes trust and increases the zero-result rate.

## Solution
Detect vague queries and ask a follow-up question before searching.

### Detection heuristics
- Query is <5 words and contains no specific nouns
- Query has no search results above similarity threshold (e.g., <0.3)
- Query matches known ambiguous patterns: "when?", "how?", "what about X?"

### Response pattern
```
User: when?
Bot: Could you clarify? For example:
- When is the application deadline?
- When do classes start?
- When is the exam?
```

### Approach
1. Run search first — if top result similarity > threshold, answer normally
2. If below threshold or zero results, generate clarification using LLM
3. Store the clarification interaction in `bot_interactions` with `status='clarification'`

## Changes
- **Helper repo:** `src/services/message_search/generate_answer.py` — add clarification logic
- **Helper repo:** `src/handlers/` — handle clarification flow

## Verification
1. Send "when?" — bot should ask for clarification
2. Send "when is the application deadline?" — bot should answer directly
3. Check `bot_interactions` — clarification interactions logged with correct status
