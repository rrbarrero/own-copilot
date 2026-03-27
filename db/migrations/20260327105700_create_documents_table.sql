-- migrate:up
CREATE TABLE documents (
    uuid UUID PRIMARY KEY,
    content TEXT NOT NULL,
    source_type VARCHAR(20) NOT NULL,
    source_id VARCHAR(255) NOT NULL,
    path TEXT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    extension VARCHAR(10) NOT NULL,
    doc_type VARCHAR(20) NOT NULL,
    language VARCHAR(50),
    repository_url TEXT,
    branch VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- migrate:down
DROP TABLE IF EXISTS documents;
