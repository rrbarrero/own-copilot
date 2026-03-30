\restrict dbmate

-- Dumped from database version 17.9 (Debian 17.9-1.pgdg12+1)
-- Dumped by pg_dump version 18.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: vector; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public;


--
-- Name: EXTENSION vector; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION vector IS 'vector data type and ivfflat and hnsw access methods';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: conversation_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversation_messages (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    conversation_id uuid NOT NULL,
    role character varying(10) NOT NULL,
    content text NOT NULL,
    rewritten_question text,
    citations_json jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    scope_type character varying(20) NOT NULL,
    repository_id uuid,
    document_id uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: document_chunks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_chunks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    document_uuid uuid NOT NULL,
    chunk_index integer NOT NULL,
    content text NOT NULL,
    embedding public.vector(1024),
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    uuid uuid NOT NULL,
    source_type character varying(20) NOT NULL,
    source_id character varying(255) NOT NULL,
    path text NOT NULL,
    filename character varying(255) NOT NULL,
    extension character varying(10) NOT NULL,
    doc_type character varying(20) NOT NULL,
    language character varying(50),
    repository_url text,
    branch character varying(100),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP,
    processing_status character varying(20) NOT NULL,
    size_bytes bigint NOT NULL,
    upload_batch_id uuid,
    repository_sync_id uuid,
    content_hash character varying(64),
    mime_type character varying(100),
    indexed_at timestamp with time zone,
    last_error text,
    version integer DEFAULT 1,
    superseded_by uuid,
    repository_id uuid
);


--
-- Name: ingestion_jobs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ingestion_jobs (
    id uuid NOT NULL,
    queue_name character varying(50) NOT NULL,
    job_type character varying(100) NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying NOT NULL,
    attempts integer DEFAULT 0 NOT NULL,
    max_attempts integer DEFAULT 5 NOT NULL,
    run_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    locked_at timestamp with time zone,
    locked_by character varying(255),
    last_error text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    priority integer DEFAULT 0 NOT NULL,
    correlation_id uuid,
    started_at timestamp with time zone,
    finished_at timestamp with time zone
);


--
-- Name: repositories; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.repositories (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    provider character varying(30) NOT NULL,
    clone_url text NOT NULL,
    normalized_clone_url text NOT NULL,
    owner character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    default_branch character varying(255),
    local_path text NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    last_synced_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: repository_syncs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.repository_syncs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    repository_id uuid NOT NULL,
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


--
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


--
-- Name: conversation_messages conversation_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_messages
    ADD CONSTRAINT conversation_messages_pkey PRIMARY KEY (id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (id);


--
-- Name: document_chunks document_chunks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_pkey PRIMARY KEY (id);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (uuid);


--
-- Name: ingestion_jobs ingestion_jobs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ingestion_jobs
    ADD CONSTRAINT ingestion_jobs_pkey PRIMARY KEY (id);


--
-- Name: repositories repositories_normalized_clone_url_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.repositories
    ADD CONSTRAINT repositories_normalized_clone_url_key UNIQUE (normalized_clone_url);


--
-- Name: repositories repositories_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.repositories
    ADD CONSTRAINT repositories_pkey PRIMARY KEY (id);


--
-- Name: repository_syncs repository_syncs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.repository_syncs
    ADD CONSTRAINT repository_syncs_pkey PRIMARY KEY (id);


--
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: idx_conv_messages_conv_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conv_messages_conv_id ON public.conversation_messages USING btree (conversation_id, created_at);


--
-- Name: idx_conversations_scope; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_scope ON public.conversations USING btree (scope_type, repository_id, document_id);


--
-- Name: idx_document_chunks_doc_uuid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_chunks_doc_uuid ON public.document_chunks USING btree (document_uuid);


--
-- Name: idx_document_chunks_embedding; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_chunks_embedding ON public.document_chunks USING hnsw (embedding public.vector_cosine_ops);


--
-- Name: idx_documents_content_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_content_hash ON public.documents USING btree (content_hash);


--
-- Name: idx_documents_repository_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_repository_id ON public.documents USING btree (repository_id);


--
-- Name: idx_documents_repository_sync_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_repository_sync_id ON public.documents USING btree (repository_sync_id);


--
-- Name: idx_documents_upload_batch_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_upload_batch_id ON public.documents USING btree (upload_batch_id);


--
-- Name: idx_ingestion_jobs_queue_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ingestion_jobs_queue_name ON public.ingestion_jobs USING btree (queue_name);


--
-- Name: idx_ingestion_jobs_status_run_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ingestion_jobs_status_run_at ON public.ingestion_jobs USING btree (status, run_at);


--
-- Name: idx_repository_syncs_repo_id_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_repository_syncs_repo_id_created ON public.repository_syncs USING btree (repository_id, created_at DESC);


--
-- Name: idx_repository_syncs_repo_id_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_repository_syncs_repo_id_status ON public.repository_syncs USING btree (repository_id, status);


--
-- Name: conversation_messages conversation_messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversation_messages
    ADD CONSTRAINT conversation_messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(id) ON DELETE CASCADE;


--
-- Name: conversations conversations_document_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_document_id_fkey FOREIGN KEY (document_id) REFERENCES public.documents(uuid);


--
-- Name: conversations conversations_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.repositories(id);


--
-- Name: document_chunks document_chunks_document_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_chunks
    ADD CONSTRAINT document_chunks_document_uuid_fkey FOREIGN KEY (document_uuid) REFERENCES public.documents(uuid) ON DELETE CASCADE;


--
-- Name: documents documents_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.repositories(id);


--
-- Name: repository_syncs repository_syncs_repository_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.repository_syncs
    ADD CONSTRAINT repository_syncs_repository_id_fkey FOREIGN KEY (repository_id) REFERENCES public.repositories(id);


--
-- PostgreSQL database dump complete
--

\unrestrict dbmate


--
-- Dbmate schema migrations
--

INSERT INTO public.schema_migrations (version) VALUES
    ('20260327105700'),
    ('20260327121038'),
    ('20260327121326'),
    ('20260327153144'),
    ('20260327153924'),
    ('20260327155454'),
    ('20260328111030'),
    ('20260329095838'),
    ('20260329105900'),
    ('20260329110800'),
    ('20260329114100'),
    ('20260330074716');
