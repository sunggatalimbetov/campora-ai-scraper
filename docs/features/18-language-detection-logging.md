# Language Detection Logging

## Priority
P5 — Future feature (helper repo)

## Problem
The bot serves Russian, Kazakh, and English speakers. We don't know if search quality differs by language — a query in Kazakh might perform worse than Russian due to the `russian` tsvector config in full-text search.

## Solution
Detect the query language and log it alongside each interaction. This enables per-language accuracy analysis.

### Approach
- Use a lightweight language detection library (e.g., `langdetect` or `lingua-py`)
- Detect language of the user's input message
- Store in the existing `user_language` column on `bot_interactions` (already exists but not populated)
- Weekly analysis: compare accuracy and zero-result rates across languages

## Changes
- **Helper repo:** `src/handlers/commands.py` + `src/handlers/messages.py` — detect and store language
- `requirements.txt` — add `langdetect` or `lingua-language-detector`

## Future consideration
- If Kazakh queries perform poorly with `russian` tsvector, consider adding a Kazakh text search config or falling back to pure semantic search for non-Russian queries

## Verification
1. Send queries in Russian, Kazakh, and English
2. Check `bot_interactions.user_language` — should show `ru`, `kk`, `en`
3. Query analytics: `SELECT user_language, COUNT(*), AVG(response_time_ms) FROM bot_interactions GROUP BY user_language`
