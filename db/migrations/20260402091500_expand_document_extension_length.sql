-- migrate:up
ALTER TABLE public.documents
ALTER COLUMN extension TYPE character varying(32);

-- migrate:down
ALTER TABLE public.documents
ALTER COLUMN extension TYPE character varying(10);
