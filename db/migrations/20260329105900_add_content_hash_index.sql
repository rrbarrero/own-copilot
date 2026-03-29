-- migrate:up
CREATE INDEX idx_documents_content_hash ON public.documents USING btree (content_hash);

-- migrate:down
DROP INDEX IF EXISTS idx_documents_content_hash;
