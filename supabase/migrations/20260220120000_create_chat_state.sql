-- Tracks per-chat scraping progress.
-- Used by both the initial batch scraper and the real-time event listener
-- to know which chats have been scraped and where to resume from.

CREATE TABLE IF NOT EXISTS public.chat_state (
	chat_id BIGINT PRIMARY KEY,
	last_message_id BIGINT NOT NULL DEFAULT 0,
	initial_scrape_done BOOLEAN NOT NULL DEFAULT FALSE,
	updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
