-- migrate:up
UPDATE documents SET processing_status = 'queued' WHERE processing_status = 'pending';
UPDATE documents SET processing_status = 'ingesting' WHERE processing_status = 'processing';
UPDATE documents SET processing_status = 'ready' WHERE processing_status = 'indexed';
UPDATE documents SET processing_status = 'error' WHERE processing_status = 'failed';

-- migrate:down
UPDATE documents SET processing_status = 'pending' WHERE processing_status = 'queued';
UPDATE documents SET processing_status = 'processing' WHERE processing_status = 'ingesting';
UPDATE documents SET processing_status = 'indexed' WHERE processing_status = 'ready';
UPDATE documents SET processing_status = 'failed' WHERE processing_status = 'error';
