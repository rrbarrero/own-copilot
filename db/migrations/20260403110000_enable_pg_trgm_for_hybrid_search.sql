-- migrate:up
CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts
ON document_chunks
USING GIN (to_tsvector('simple', content));

CREATE INDEX IF NOT EXISTS idx_document_chunks_content_trgm
ON document_chunks
USING GIN (lower(content) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_documents_path_trgm
ON documents
USING GIN (lower(path) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_documents_filename_trgm
ON documents
USING GIN (lower(filename) gin_trgm_ops);

-- migrate:down
DROP INDEX IF EXISTS idx_documents_filename_trgm;
DROP INDEX IF EXISTS idx_documents_path_trgm;
DROP INDEX IF EXISTS idx_document_chunks_content_trgm;
DROP INDEX IF EXISTS idx_document_chunks_content_fts;
-- DROP EXTENSION IF EXISTS pg_trgm;
