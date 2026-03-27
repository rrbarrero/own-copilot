-- migrate:up
ALTER TABLE public.documents DROP COLUMN IF EXISTS embedding;

CREATE TABLE public.document_chunks (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_uuid uuid NOT NULL REFERENCES public.documents(uuid) ON DELETE CASCADE,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    embedding vector(1024),
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_document_chunks_doc_uuid ON public.document_chunks(document_uuid);
CREATE INDEX idx_document_chunks_embedding ON public.document_chunks USING hnsw (embedding vector_cosine_ops);

-- migrate:down
DROP TABLE IF EXISTS public.document_chunks;
ALTER TABLE public.documents ADD COLUMN embedding vector(1024);
