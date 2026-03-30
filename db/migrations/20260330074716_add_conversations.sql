-- migrate:up
CREATE TABLE conversations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scope_type      VARCHAR(20)  NOT NULL,  -- 'repository' | 'document'
    repository_id   UUID         REFERENCES repositories(id),
    document_id     UUID         REFERENCES documents(uuid),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conversations_scope ON conversations (scope_type, repository_id, document_id);

CREATE TABLE conversation_messages (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id     UUID         NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role                VARCHAR(10)  NOT NULL,  -- 'user' | 'assistant'
    content             TEXT         NOT NULL,
    rewritten_question  TEXT,                    -- solo para role='user'
    citations_json      JSONB,                   -- solo para role='assistant'
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_conv_messages_conv_id ON conversation_messages (conversation_id, created_at);

-- migrate:down
DROP TABLE conversation_messages;
DROP TABLE conversations;

