\restrict dbmate

-- Dumped from database version 17.9
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

SET default_tablespace = '';

SET default_table_access_method = heap;

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
    superseded_by uuid
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
-- Name: schema_migrations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.schema_migrations (
    version character varying NOT NULL
);


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
-- Name: schema_migrations schema_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.schema_migrations
    ADD CONSTRAINT schema_migrations_pkey PRIMARY KEY (version);


--
-- Name: idx_ingestion_jobs_queue_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ingestion_jobs_queue_name ON public.ingestion_jobs USING btree (queue_name);


--
-- Name: idx_ingestion_jobs_status_run_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ingestion_jobs_status_run_at ON public.ingestion_jobs USING btree (status, run_at);


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
    ('20260327121326');
