-- Runs once on first Postgres boot (docker-entrypoint-initdb.d).
-- Creates a NON-superuser application role. The backend connects as this role,
-- which is subject to Row-Level Security policies — the real tenant-isolation guarantee.
-- (A superuser would bypass RLS, so we deliberately avoid connecting as one.)

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'creditiq_app') THEN
      CREATE ROLE creditiq_app LOGIN PASSWORD 'creditiq_app_password' NOSUPERUSER NOCREATEDB NOCREATEROLE;
   END IF;
END
$$;

GRANT CONNECT ON DATABASE creditiq TO creditiq_app;
GRANT USAGE, CREATE ON SCHEMA public TO creditiq_app;

-- Ensure the app role can use tables/sequences created later (by bootstrap, running as this role).
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO creditiq_app;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO creditiq_app;
