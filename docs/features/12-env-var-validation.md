# Validate Environment Variables at Startup

## Priority
P2 — Reliability

## Problem
Missing env vars cause cryptic runtime errors deep in the pipeline (e.g., `NoneType` errors when trying to create Supabase client, or `int("0")` for API ID). No fast-fail at startup.

## Solution
Add validation in `src/config/settings.py` that checks all required vars at import time and exits with a clear error message listing what's missing.

Required vars: `OPENAI_API_KEY`, `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `APP_API_ID`, `APP_API_HASH`, `TELEGRAM_SESSION`.

```python
_REQUIRED = {
    "OPENAI_API_KEY": OPENAI_API_KEY,
    "SUPABASE_URL": SUPABASE_URL,
    ...
}
_missing = [name for name, val in _REQUIRED.items() if not val]
if _missing:
    print(f"ERROR: Missing required environment variables: {', '.join(_missing)}", file=sys.stderr)
    sys.exit(1)
```

## Files to Change
- `src/config/settings.py`

## Verification
1. Remove one env var from `.env` — should fail immediately with clear message
2. With all vars present — should start normally
