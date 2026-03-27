# Extract Magic Numbers to Config

## Priority
P4 — Code quality

## Problem
Hardcoded values scattered across multiple files: batch sizes, sleep durations, max depth, flush thresholds. Changing them requires editing source files and knowing which file contains what.

## Solution
Centralize all tunable constants in `src/config/settings.py` or a separate `src/config/constants.py`.

### Constants to extract
| Current location | Value | Proposed name |
|---|---|---|
| `filter_messages_by_importance.py` | `batch_size=20` | `FILTER_BATCH_SIZE` |
| `save_messages_batch.py` | `batch_size=10` | `EMBED_BATCH_SIZE` |
| `save_messages_batch.py` | `time.sleep(1)` | `SUPABASE_BATCH_PAUSE` |
| `filter_messages_by_importance.py` | `time.sleep(1)` | `FILTER_BATCH_PAUSE` |
| `build_reply_chains.py` | `max_depth=5` | `REPLY_CHAIN_MAX_DEPTH` |
| `get_existing_message_ids.py` | `batch_size=1000` | `EXISTING_IDS_BATCH_SIZE` |
| `message_buffer.py` | `flush_threshold=1000` | `BUFFER_FLUSH_THRESHOLD` |
| `message_buffer.py` | `flush_interval=604800` | `BUFFER_FLUSH_INTERVAL` |
| `filter_messages_by_importance.py` | `text[:500]` | `FILTER_TEXT_MAX_LENGTH` |
| `filter_messages_by_importance.py` | `text[:300]` | `FILTER_REPLY_TEXT_MAX_LENGTH` |

## Files to Change
- `src/config/settings.py` or new `src/config/constants.py`
- All files listed above — import constants instead of hardcoding

## Verification
1. Change a constant value — behavior should change accordingly
2. Grep for remaining magic numbers in `src/`
