-- Switch full-text search from 'simple' to 'russian' config
-- This enables proper Russian stemming and stop word removal

-- 1. Re-populate text_search column with Russian stemming for ALL rows
UPDATE public.messages SET text_search = to_tsvector('russian', COALESCE(text, ''));

-- 2. Update trigger to use Russian config for new/updated rows
CREATE OR REPLACE FUNCTION public.messages_text_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.text_search := to_tsvector('russian', COALESCE(NEW.text, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- 3. Update hybrid_search function to query with Russian config
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
        FULL OUTER JOIN full_text_search fts ON ss.id = fts.id
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
