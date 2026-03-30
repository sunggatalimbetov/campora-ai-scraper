# Recency-Weighted Search Ranking

## Priority
P2 — Medium priority (DB migration + helper repo)

## Problem
Search ranking is based purely on vector similarity (cosine distance). A message from 2022 with high semantic similarity ranks above a message from 2025 that is equally or slightly less similar. For applicant questions about scores, deadlines, and competition stats, recent data is almost always more reliable.

## Solution
Blend vector similarity with a recency score when ranking results. Newer messages get a boost; older messages are gently penalized.

### Recency score formula
```
days_old = EXTRACT(EPOCH FROM (NOW() - m.created_at)) / 86400
recency_score = exp(-days_old / 365.0)   -- half-life: ~1 year
```

This gives:
- A message from today → recency_score ≈ 1.0
- A message from 6 months ago → recency_score ≈ 0.60
- A message from 2 years ago → recency_score ≈ 0.13

### Combined ranking
```
final_score = (similarity * 0.8) + (recency_score * 0.2)
```

Weights are tunable. Start at 80/20 to avoid degrading semantic quality.

### Messages without `created_at`
Use a neutral fallback: `recency_score = 0.5`. This avoids penalizing messages scraped before the `created_at` column was added.

## Implementation

### Option A: SQL-level (preferred)
Modify `match_messages` and `hybrid_search` RPCs in a new migration to incorporate the recency factor into ordering.

```sql
-- In match_messages
ORDER BY (0.8 * (1 - (m.embedding <=> query_embedding)) +
          0.2 * exp(-EXTRACT(EPOCH FROM (NOW() - m.created_at)) / 31536000.0)) DESC
```

Requires a new migration. The `match_messages_and_questions` RPC should also be updated.

### Option B: Application-level (helper repo)
Re-rank results in Python after fetching from Supabase. Simpler to tune without DB migrations, but fetches more rows than needed.

```python
def recency_score(created_at: datetime | None, half_life_days: int = 365) -> float:
    if not created_at:
        return 0.5
    days_old = (datetime.now(timezone.utc) - created_at).days
    return math.exp(-days_old / half_life_days)

def rerank(results, similarity_weight=0.8, recency_weight=0.2):
    for r in results:
        r["final_score"] = (
            similarity_weight * r["similarity"] +
            recency_weight * recency_score(r["created_at"])
        )
    return sorted(results, key=lambda r: r["final_score"], reverse=True)
```

**Recommendation:** Start with Option B (application-level) for fast iteration, then move to Option A once weights are validated.

## Coverage Gap
Many messages currently have `created_at = NULL` because the column was added in migration `20260323000000` and existing rows were not backfilled. Before recency weighting has full effect, either:
- Backfill `created_at` from Telegram message IDs (Telegram IDs encode the timestamp)
- Accept the 0.5 neutral fallback for unbackfilled messages

## Changes
- **Helper repo:** `src/services/message_search/` — add `rerank()` function, apply after fetching results
- **Scraper repo:** new migration to update `match_messages` and `hybrid_search` RPCs (Phase 2)

## Verification
1. Ask "какой проходной балл на CS?" — verify that 2025 messages rank above 2022 messages with similar similarity scores
2. Compare rankings before/after: log `similarity` and `final_score` for the same query
3. Confirm the 80/20 split does not degrade satisfaction rate (track likes/dislikes)
