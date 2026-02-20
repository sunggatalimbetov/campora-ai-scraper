-- Question generation: store hypothetical questions per message for improved retrieval
-- Run after 002_hybrid_search.sql

-- Table to store generated questions and their embeddings
CREATE TABLE IF NOT EXISTS public.message_questions (
    id SERIAL PRIMARY KEY,
    message_id BIGINT NOT NULL REFERENCES public.messages(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for vector similarity search on question embeddings
CREATE INDEX IF NOT EXISTS message_questions_embedding_idx
ON public.message_questions
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Index for fast lookups by message_id (e.g. checking which messages already have questions)
CREATE INDEX IF NOT EXISTS message_questions_message_id_idx
ON public.message_questions (message_id);

-- Combined search RPC: searches both messages and message_questions embeddings,
-- deduplicates by message_id keeping the highest similarity score.
CREATE OR REPLACE FUNCTION public.match_messages_and_questions(
    query_embedding vector(1536),
    match_count int DEFAULT 5
)
RETURNS TABLE (
    id BIGINT,
    chat_id BIGINT,
    author BIGINT,
    text text,
    link text,
    reply_to_message_id BIGINT,
    similarity float,
    match_source text  -- 'message' or 'question'
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH message_matches AS (
        SELECT
            m.id,
            m.chat_id,
            m.author,
            m.text,
            m.link,
            m.reply_to_message_id,
            (1 - (m.embedding <=> query_embedding))::float AS similarity,
            'message'::text AS match_source
        FROM public.messages m
        WHERE m.embedding IS NOT NULL
        ORDER BY m.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    question_matches AS (
        SELECT
            mq.message_id AS id,
            m.chat_id,
            m.author,
            m.text,
            m.link,
            m.reply_to_message_id,
            (1 - (mq.embedding <=> query_embedding))::float AS similarity,
            'question'::text AS match_source
        FROM public.message_questions mq
        JOIN public.messages m ON m.id = mq.message_id
        WHERE mq.embedding IS NOT NULL
        ORDER BY mq.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT * FROM message_matches
        UNION ALL
        SELECT * FROM question_matches
    ),
    deduplicated AS (
        SELECT DISTINCT ON (c.id)
            c.id,
            c.chat_id,
            c.author,
            c.text,
            c.link,
            c.reply_to_message_id,
            c.similarity,
            c.match_source
        FROM combined c
        ORDER BY c.id, c.similarity DESC
    )
    SELECT
        d.id,
        d.chat_id,
        d.author,
        d.text,
        d.link,
        d.reply_to_message_id,
        d.similarity,
        d.match_source
    FROM deduplicated d
    ORDER BY d.similarity DESC
    LIMIT match_count;
END;
$$;
