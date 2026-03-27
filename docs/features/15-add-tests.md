# Add Test Coverage

## Priority
P4 — Code quality

## Problem
Zero test coverage. No `tests/` directory, no pytest config, no CI test step. Regressions can only be caught manually.

## Solution
Add pytest with unit tests for the most critical and testable modules first, then expand.

### Phase 1: Unit tests (no external deps)
- `src/realtime/pre_filter.py` — test `should_buffer()` with various inputs
- `src/scraper/filter_messages_by_importance.py` — test `_parse_valuable_ids()` and `_expand_reply_chains()` (pure logic, no API calls)
- `src/scraper/build_reply_chains.py` — test `_resolve_chain()` with mock batch data

### Phase 2: Integration tests (mocked externals)
- `src/scraper/save_messages_batch.py` — mock Supabase + OpenAI, verify upsert called correctly
- `src/realtime/message_buffer.py` — mock pipeline, verify flush triggers at threshold
- `src/scraper/chat_state.py` — mock Supabase, verify get/upsert

### Phase 3: End-to-end
- Full pipeline test with mocked Telegram + OpenAI + Supabase
- Verify message flow: fetch → filter → embed → save → state update

## Files to Create
- `tests/conftest.py` — shared fixtures
- `tests/test_pre_filter.py`
- `tests/test_parse_valuable_ids.py`
- `tests/test_reply_chains.py`
- `tests/test_message_buffer.py`
- `pytest.ini` or `pyproject.toml` pytest config

## Setup
```
pip install pytest pytest-asyncio
```

Add to `requirements.txt` (dev section) or create `requirements-dev.txt`.

## Verification
1. `pytest` — all tests pass
2. `pytest --cov` — see coverage report
