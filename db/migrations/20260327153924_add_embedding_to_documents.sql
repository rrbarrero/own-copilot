-- migrate:up
ALTER TABLE public.documents ADD COLUMN embedding vector(1024);
CREATE INDEX ON public.documents USING hnsw (embedding vector_cosine_ops);

-- migrate:down
-- ALTER TABLE public.documents DROP COLUMN embedding;
