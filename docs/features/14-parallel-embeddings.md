# Parallel Embedding Generation

## Priority
P3 — Performance

## Problem
Embeddings are generated sequentially — one API call per message within each batch. For large scrapes, this adds significant latency on top of the AI filter.

## Solution
Use OpenAI's batch embedding endpoint which accepts multiple texts in a single API call (up to 2048 inputs). This eliminates per-message round-trip overhead.

### Approach
1. Collect all texts in a batch (up to `batch_size` messages)
2. Send a single `embeddings.create(input=[text1, text2, ...])` call
3. Map returned embeddings back to their messages by index

```python
def get_embeddings_batch(texts: List[str]) -> List[List[float]]:
    response = client_oa.embeddings.create(
        model="text-embedding-3-small",
        input=texts,
    )
    return [item.embedding for item in response.data]
```

### Alternative: asyncio.gather()
If keeping per-message calls, wrap in async and use `asyncio.gather()` for concurrent requests. Less efficient than batch endpoint but simpler change.

## Files to Change
- `src/scraper/get_embedding.py` — add `get_embeddings_batch()` function
- `src/scraper/save_messages_batch.py` — use batch embedding instead of per-message loop

## Verification
1. Compare embedding output for same text — should be identical
2. Measure time for 100 messages: sequential vs batch
3. Full pipeline test to ensure no regression
