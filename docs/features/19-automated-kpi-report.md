# Automated KPI Report to Discord

## Priority
P5 — Future feature

## Problem
No automated way to track bot health metrics. Accuracy, response time, usage per group, and zero-result rates require manual SQL queries.

## Solution
Weekly cron job that queries `bot_interactions` and posts a summary to a Discord webhook.

### Metrics to include
- Total queries (this week vs last week)
- Average response time (target: <5s)
- Zero-result rate (target: <20%)
- Thumbs up/down ratio
- Top 5 unanswered queries
- Queries per group (chat_id)
- Active unique users

### Architecture
```
GitHub Actions cron (weekly) → Python script → Supabase query → Discord webhook
```

### Alternative: standalone cron
Run as a Docker container on a schedule, or use Supabase Edge Functions.

## Changes
- New script: `scripts/weekly_kpi_report.py`
- New env var: `DISCORD_WEBHOOK_URL`
- GitHub Actions workflow: `.github/workflows/weekly-kpi.yml` (cron: `0 9 * * 1`)

## Verification
1. Run script manually — should post formatted message to Discord
2. Verify all metrics match manual SQL queries
3. Trigger GitHub Action — should succeed
