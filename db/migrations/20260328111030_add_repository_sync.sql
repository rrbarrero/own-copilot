-- migrate:up
CREATE TABLE repositories (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    provider character varying(30) NOT NULL,
    clone_url text NOT NULL,
    normalized_clone_url text NOT NULL UNIQUE,
    owner character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    default_branch character varying(255),
    local_path text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    last_synced_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE repository_syncs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id uuid NOT NULL REFERENCES repositories(id),
    branch character varying(255) NOT NULL,
    commit_sha character varying(64),
    status character varying(20) NOT NULL,
    started_at timestamp with time zone NOT NULL,
    finished_at timestamp with time zone,
    last_error text,
    scanned_files integer DEFAULT 0 NOT NULL,
    changed_files integer DEFAULT 0 NOT NULL,
    deleted_files integer DEFAULT 0 NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);

-- New indices for repository_syncs
CREATE INDEX idx_repository_syncs_repo_id_created ON repository_syncs(repository_id, created_at DESC);
CREATE INDEX idx_repository_syncs_repo_id_status ON repository_syncs(repository_id, status);

-- Add repository_id to documents
ALTER TABLE documents ADD COLUMN repository_id uuid REFERENCES repositories(id);

-- New indices for documents
CREATE INDEX idx_documents_upload_batch_id ON documents(upload_batch_id);
CREATE INDEX idx_documents_repository_sync_id ON documents(repository_sync_id);
CREATE INDEX idx_documents_repository_id ON documents(repository_id);

-- migrate:down
DROP INDEX IF EXISTS idx_documents_repository_id;
DROP INDEX IF EXISTS idx_documents_repository_sync_id;
DROP INDEX IF EXISTS idx_documents_upload_batch_id;
ALTER TABLE documents DROP COLUMN repository_id;
DROP TABLE repository_syncs;
DROP TABLE repositories;
