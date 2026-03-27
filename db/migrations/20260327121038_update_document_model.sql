-- migrate:up
ALTER TABLE documents ADD COLUMN processing_status VARCHAR(20) NOT NULL DEFAULT 'pending';
ALTER TABLE documents ADD COLUMN size_bytes BIGINT NOT NULL DEFAULT 0;
ALTER TABLE documents ADD COLUMN upload_batch_id UUID;
ALTER TABLE documents ADD COLUMN repository_sync_id UUID;
ALTER TABLE documents ADD COLUMN content_hash VARCHAR(64);
ALTER TABLE documents ADD COLUMN mime_type VARCHAR(100);
ALTER TABLE documents ADD COLUMN indexed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE documents ADD COLUMN last_error TEXT;
ALTER TABLE documents ADD COLUMN version INT DEFAULT 1;
ALTER TABLE documents ADD COLUMN superseded_by UUID;

-- Remove the default values now that columns are created
ALTER TABLE documents ALTER COLUMN processing_status DROP DEFAULT;
ALTER TABLE documents ALTER COLUMN size_bytes DROP DEFAULT;

-- Remove content from DB as it is now in the filesystem
ALTER TABLE documents DROP COLUMN content;

-- migrate:down
ALTER TABLE documents ADD COLUMN content TEXT;
ALTER TABLE documents DROP COLUMN processing_status;
ALTER TABLE documents DROP COLUMN size_bytes;
ALTER TABLE documents DROP COLUMN upload_batch_id;
ALTER TABLE documents DROP COLUMN repository_sync_id;
ALTER TABLE documents DROP COLUMN content_hash;
ALTER TABLE documents DROP COLUMN mime_type;
ALTER TABLE documents DROP COLUMN indexed_at;
ALTER TABLE documents DROP COLUMN last_error;
ALTER TABLE documents DROP COLUMN version;
ALTER TABLE documents DROP COLUMN superseded_by;
