## Current State

Your Telegram bot is a **knowledge assistant** that searches through university/community group chat history using hybrid search (vector + full-text) and generates AI-powered answers with GPT-4o-mini. It has a solid data pipeline that scrapes Telegram channels, filters messages by importance, resolves reply chains, and stores everything with embeddings in Supabase. You also have interaction logging with feedback (like/dislike) -- a strong foundation.

---

## Suggested Next Steps (roughly prioritized)

### 1. **Real-time message ingestion**

Right now your scraper runs in batches. Hooking into Telegram's real-time updates (via Telethon's event handlers) so new messages get indexed immediately would keep the knowledge base fresh without manual runs.

### 2. **Multi-turn conversations**

Currently each `/ask` is stateless. Adding session/conversation memory would let users ask follow-up questions naturally -- e.g., "What about the deadline?" after asking about course registration.

### 3. **Caching frequent queries**

University communities tend to ask the same questions repeatedly ("When is the deadline?", "How to register?"). A Redis or in-memory cache keyed on query embeddings (with similarity threshold) could dramatically reduce latency and API costs.

### 4. **Analytics dashboard**

You're already logging interactions and feedback to `bot_interactions`. Building a simple dashboard (even a Streamlit app) to visualize popular queries, response quality (feedback ratios), latency trends, and search hit rates would help you iterate on quality.

### 5. **Query rewriting / expansion**

Before searching, use a lightweight LLM call to reformulate vague or misspelled user queries into clearer search terms. This is especially valuable with multi-language users who might mix Russian, Kazakh, and English.

### 6. **Improved citation / source attribution**

When generating answers, link back to the original messages (with timestamps, authors, or links to the Telegram message). This builds trust and lets users verify information.

### 7. **Proactive notifications**

Detect important announcements (deadlines, schedule changes) in real-time and proactively notify subscribed users -- turning the bot from reactive Q&A into an active information service.

### 8. **Evaluation & A/B testing**

You have an evaluation framework in `tests/evaluation/`. Expanding it with a golden test set and running systematic A/B tests on search strategies (e.g., different hybrid weights, with/without question embeddings) would help you measure and improve search quality over time.

### 9. **Web frontend / API layer**

Exposing the search as a REST API would let you build a web interface alongside the Telegram bot, making the knowledge base accessible to people who prefer browsing over chatting.
