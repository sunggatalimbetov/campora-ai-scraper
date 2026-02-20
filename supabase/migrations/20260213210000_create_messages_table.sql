-- Enable pgvector extension (required for embedding column)
CREATE EXTENSION IF NOT EXISTS vector;

-- Messages table used by data_scraper and message_search
-- Embedding dimension 1536 = OpenAI text-embedding-3-small
CREATE TABLE IF NOT EXISTS public.messages (
    id BIGINT PRIMARY KEY,
    chat_id BIGINT NOT NULL,
    author BIGINT,
    text TEXT NOT NULL,
    link TEXT NOT NULL,
    embedding vector(1536),
    reply_to_message_id BIGINT
);

-- RPC used by message_search.search_messages()
CREATE OR REPLACE FUNCTION public.match_messages(
    query_embedding vector(1536),
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id BIGINT,
    chat_id BIGINT,
    author BIGINT,
    text TEXT,
    link TEXT,
    reply_to_message_id BIGINT,
    similarity float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.chat_id,
        m.author,
        m.text,
        m.link,
        m.reply_to_message_id,
        (1 - (m.embedding <=> query_embedding))::float AS similarity
    FROM public.messages m
    WHERE m.embedding IS NOT NULL
    ORDER BY m.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
