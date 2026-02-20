-- Change messages PK from (id) to (id, chat_id)
-- Telegram message IDs are only unique within a single chat, not globally.
-- This migration makes the schema correctly handle multiple chats.

-- 1. Drop FK from message_questions -> messages (references old single-column PK)
ALTER TABLE public.message_questions
    DROP CONSTRAINT IF EXISTS message_questions_message_id_fkey;

-- 2. Add chat_id column to message_questions so we can reference the composite PK
ALTER TABLE public.message_questions
    ADD COLUMN IF NOT EXISTS chat_id BIGINT;

-- 3. Backfill chat_id in message_questions from the messages table
UPDATE public.message_questions mq
SET chat_id = m.chat_id
FROM public.messages m
WHERE mq.message_id = m.id
  AND mq.chat_id IS NULL;

-- 4. Make chat_id NOT NULL now that it's populated
ALTER TABLE public.message_questions
    ALTER COLUMN chat_id SET NOT NULL;

-- 5. Drop the old single-column PK on messages
ALTER TABLE public.messages
    DROP CONSTRAINT messages_pkey;

-- 6. Add the composite PK
ALTER TABLE public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (id, chat_id);

-- 7. Re-add FK from message_questions referencing the composite PK
ALTER TABLE public.message_questions
    ADD CONSTRAINT message_questions_message_id_chat_id_fkey
    FOREIGN KEY (message_id, chat_id) REFERENCES public.messages(id, chat_id)
    ON DELETE CASCADE;

-- 8. Update hybrid_search: join on (id, chat_id) to avoid cross-chat collisions
CREATE OR REPLACE FUNCTION public.hybrid_search(
    query_text text,
    query_embedding vector(1536),
    match_count int DEFAULT 10,
    full_text_weight float DEFAULT 0.5,
    semantic_weight float DEFAULT 0.5,
    rrf_k int DEFAULT 60
)
RETURNS TABLE (
    id BIGINT,
    chat_id BIGINT,
    author BIGINT,
    text text,
    link text,
    reply_to_message_id BIGINT,
    semantic_similarity float,
    full_text_rank float,
    combined_score float
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH semantic_search AS (
        SELECT
            m.id,
            m.chat_id,
            m.author,
            m.text,
            m.link,
            m.reply_to_message_id,
            (1 - (m.embedding <=> query_embedding))::float as similarity,
            ROW_NUMBER() OVER (ORDER BY m.embedding <=> query_embedding) as rank
        FROM public.messages m
        WHERE m.embedding IS NOT NULL
        ORDER BY m.embedding <=> query_embedding
        LIMIT match_count * 2
    ),
    full_text_search AS (
        SELECT
            m.id,
            m.chat_id,
            m.author,
            m.text,
            m.link,
            m.reply_to_message_id,
            ts_rank_cd(m.text_search, websearch_to_tsquery('russian', query_text)) as rank_score,
            ROW_NUMBER() OVER (
                ORDER BY ts_rank_cd(m.text_search, websearch_to_tsquery('russian', query_text)) DESC
            ) as rank
        FROM public.messages m
        WHERE m.text_search IS NOT NULL
          AND trim(COALESCE(query_text, '')) <> ''
          AND m.text_search @@ websearch_to_tsquery('russian', query_text)
        ORDER BY rank_score DESC
        LIMIT match_count * 2
    ),
    combined AS (
        SELECT
            COALESCE(ss.id, fts.id) as id,
            COALESCE(ss.chat_id, fts.chat_id) as chat_id,
            COALESCE(ss.author, fts.author) as author,
            COALESCE(ss.text, fts.text) as text,
            COALESCE(ss.link, fts.link) as link,
            COALESCE(ss.reply_to_message_id, fts.reply_to_message_id) as reply_to_message_id,
            COALESCE(ss.similarity, 0.0)::double precision as semantic_similarity,
            COALESCE(fts.rank_score, 0.0)::double precision as full_text_rank,
            (COALESCE(semantic_weight / (rrf_k + ss.rank), 0.0) +
             COALESCE(full_text_weight / (rrf_k + fts.rank), 0.0))::double precision as combined_score
        FROM semantic_search ss
        FULL OUTER JOIN full_text_search fts
            ON ss.id = fts.id AND ss.chat_id = fts.chat_id
    )
    SELECT
        c.id,
        c.chat_id,
        c.author,
        c.text,
        c.link,
        c.reply_to_message_id,
        c.semantic_similarity,
        c.full_text_rank,
        c.combined_score
    FROM combined c
    ORDER BY c.combined_score DESC
    LIMIT match_count;
END;
$$;

-- 9. Update match_messages_and_questions: join and deduplicate on (id, chat_id)
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
    match_source text
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
        JOIN public.messages m ON m.id = mq.message_id AND m.chat_id = mq.chat_id
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
        SELECT DISTINCT ON (c.id, c.chat_id)
            c.id,
            c.chat_id,
            c.author,
            c.text,
            c.link,
            c.reply_to_message_id,
            c.similarity,
            c.match_source
        FROM combined c
        ORDER BY c.id, c.chat_id, c.similarity DESC
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
