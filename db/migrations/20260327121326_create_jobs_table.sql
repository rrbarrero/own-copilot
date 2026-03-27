-- migrate:up
CREATE TABLE ingestion_jobs (
    id UUID PRIMARY KEY,
    queue_name VARCHAR(50) NOT NULL,
    job_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    attempts INT NOT NULL DEFAULT 0,
    max_attempts INT NOT NULL DEFAULT 5,
    run_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP WITH TIME ZONE,
    locked_by VARCHAR(255),
    last_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    priority INT NOT NULL DEFAULT 0,
    correlation_id UUID,
    started_at TIMESTAMP WITH TIME ZONE,
    finished_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_ingestion_jobs_status_run_at ON ingestion_jobs (status, run_at);
CREATE INDEX idx_ingestion_jobs_queue_name ON ingestion_jobs (queue_name);

-- migrate:down
DROP TABLE IF EXISTS ingestion_jobs;
