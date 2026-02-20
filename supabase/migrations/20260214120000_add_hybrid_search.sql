-- Hybrid search: add full-text search column and hybrid_search RPC
-- Run after 001_messages_table_and_match.sql

-- Add tsvector column for full-text search
ALTER TABLE public.messages ADD COLUMN IF NOT EXISTS text_search tsvector;

-- Populate the column for existing rows
UPDATE public.messages SET text_search = to_tsvector('russian', COALESCE(text, '')) WHERE text_search IS NULL;

-- Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS messages_text_search_idx ON public.messages USING GIN (text_search);

-- Create trigger function to auto-populate text_search on insert/update
CREATE OR REPLACE FUNCTION public.messages_text_search_trigger() RETURNS trigger AS $$
BEGIN
    NEW.text_search := to_tsvector('russian', COALESCE(NEW.text, ''));
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

-- Attach trigger
DROP TRIGGER IF EXISTS messages_text_search_update ON public.messages;
CREATE TRIGGER messages_text_search_update
    BEFORE INSERT OR UPDATE ON public.messages
    FOR EACH ROW EXECUTE FUNCTION public.messages_text_search_trigger();

-- Hybrid search RPC: combines vector similarity + full-text search via RRF
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
