# Replace print() with Python logging Module

## Priority
P2 — Reliability

## Problem
All output uses `print()` with emoji prefixes. No log levels, no timestamps, no structured output. Hard to debug in production/Docker — can't filter by severity, can't route to files or monitoring.

## Solution
Replace all `print()` calls with `logging.getLogger(__name__)` using appropriate levels:
- `logger.info()` for normal progress (batch saved, scrape started)
- `logger.warning()` for recoverable issues (DB lookup failed, falling back)
- `logger.error()` for failures (API error, message save failed)

Configure logging once in `main.py`:
```python
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
```

## Files to Change
- `main.py` — add `logging.basicConfig()` configuration
- `src/scraper/fetch_channel_messages.py`
- `src/scraper/filter_messages_by_importance.py`
- `src/scraper/save_messages_batch.py`
- `src/scraper/build_reply_chains.py`
- `src/scraper/get_existing_message_ids.py`
- `src/scraper/scrape_channel.py`
- `src/realtime/main.py`
- `src/realtime/initial_scrape.py`
- `src/realtime/message_buffer.py`
- `src/realtime/signal_handlers.py`

## Verification
1. Run `python main.py` — output should show timestamps and log levels
2. Grep for `print(` in `src/` — should return zero results
3. Docker logs should be parseable by log aggregators
