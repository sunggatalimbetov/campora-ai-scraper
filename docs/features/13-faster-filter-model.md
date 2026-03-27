# Evaluate Faster/Cheaper Filter Model

## Priority
P3 — Performance

## Problem
GPT-4o-mini is the bottleneck in the scraping pipeline. For large groups (600K+ messages), the AI filter takes the majority of processing time. At ~$0.15/M input tokens, it's also the largest cost driver.

## Solution
Benchmark alternative models for the importance filter:
- **Groq Llama 3.1 8B** — ~50x cheaper ($0.05/M tokens), significantly faster due to Groq's inference speed
- **Groq Llama 3.3 70B** — more capable, still much cheaper than GPT-4o-mini

### Steps
1. Run the same 1000-message sample through GPT-4o-mini and Groq Llama 3.1 8B
2. Compare keep/filter decisions (measure agreement rate)
3. If agreement >90%, switch to Groq for batch scraping (keep GPT-4o-mini as fallback)
4. Test with batch_size=100 (up from 20) — Groq handles larger contexts well

### Cost comparison
| Model | Cost/M input tokens | Speed |
|-------|-------------------|-------|
| GPT-4o-mini | $0.15 | Moderate |
| Groq Llama 3.1 8B | $0.05 | Very fast |
| Groq Llama 3.3 70B | $0.59 | Fast |

## Files to Change
- `src/scraper/filter_messages_by_importance.py` — add model parameter or switch client
- `src/config/settings.py` — add `GROQ_API_KEY` if using Groq
- `requirements.txt` — add `groq` if using Groq SDK

## Risks
- Batch size >50 may reduce filter quality — benchmark before committing
- Groq rate limits differ from OpenAI — may need different batch pacing

## Verification
1. Run benchmark script comparing models on same message set
2. Measure: agreement rate, false positive rate, processing time, cost
3. Full pipeline test on a medium group (10K messages)
