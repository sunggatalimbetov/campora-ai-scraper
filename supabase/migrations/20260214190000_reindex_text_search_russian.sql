-- Force re-index all text_search values with Russian config
-- Run in batches to avoid statement timeout

-- Batch 1: first 3000
UPDATE public.messages
SET text_search = to_tsvector('russian', COALESCE(text, ''))
WHERE id IN (SELECT id FROM public.messages ORDER BY id LIMIT 3000);

-- Batch 2: next 3000
UPDATE public.messages
SET text_search = to_tsvector('russian', COALESCE(text, ''))
WHERE id IN (SELECT id FROM public.messages ORDER BY id LIMIT 3000 OFFSET 3000);

-- Batch 3: remaining
UPDATE public.messages
SET text_search = to_tsvector('russian', COALESCE(text, ''))
WHERE id IN (SELECT id FROM public.messages ORDER BY id LIMIT 3000 OFFSET 6000);

-- Drop test function
DROP FUNCTION IF EXISTS public.test_tsvector(text);
