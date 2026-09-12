-- What hosted Supabase provides and a bare Postgres does not.
--
-- The migrations reference auth.uid(), auth.jwt(), auth.role(), auth.users and
-- the authenticated / service_role / anon roles. These are recreated with the
-- same shapes and the same semantics, not as stubs that merely satisfy a
-- parser: auth.uid() really does read request.jwt.claims, which is how the
-- tests switch identity and how RLS then behaves exactly as it will in
-- production.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS pgtap;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$ BEGIN
  CREATE ROLE authenticated NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE ROLE service_role NOLOGIN BYPASSRLS;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE ROLE anon NOLOGIN;
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
  id    uuid PRIMARY KEY,
  email text
);

-- Supabase resolves these from the request JWT claims, which the tests set
-- with set_config. This is that behaviour, not a different one.
-- COALESCE to an empty object first. set_config(..., NULL, ...) stores an
-- empty string, and ''::json raises 22P02 rather than returning NULL, so an
-- unauthenticated caller got a json syntax error where production returns NULL.
CREATE OR REPLACE FUNCTION auth.uid() RETURNS uuid
LANGUAGE sql STABLE AS $fn$
  SELECT NULLIF(
    COALESCE(NULLIF(current_setting('request.jwt.claims', true), ''), '{}')::json->>'sub',
    '')::uuid;
$fn$;

CREATE OR REPLACE FUNCTION auth.jwt() RETURNS jsonb
LANGUAGE sql STABLE AS $fn$
  SELECT COALESCE(
    NULLIF(current_setting('request.jwt.claims', true), '')::jsonb,
    '{}'::jsonb);
$fn$;

CREATE OR REPLACE FUNCTION auth.role() RETURNS text
LANGUAGE sql STABLE AS $fn$
  SELECT COALESCE(
    NULLIF(COALESCE(NULLIF(current_setting('request.jwt.claims', true), ''), '{}')::json->>'role', ''),
    'anon');
$fn$;

CREATE OR REPLACE FUNCTION auth.email() RETURNS text
LANGUAGE sql STABLE AS $fn$
  SELECT NULLIF(
    COALESCE(NULLIF(current_setting('request.jwt.claims', true), ''), '{}')::json->>'email', '');
$fn$;

GRANT USAGE ON SCHEMA public, auth TO authenticated, service_role, anon;
GRANT SELECT ON auth.users TO authenticated, service_role;

-- Supabase grants table privileges to these roles through default privileges
-- on the public schema, which is why its migrations create tables without a
-- GRANT and the policies still apply to a signed-in user. A bare Postgres does
-- not, so 'permission denied for table portfolio_imports' is an artefact of
-- the harness rather than of the schema.
--
-- Reproducing the default privileges is the faithful fix. Adding explicit
-- grants to the migrations instead would make them differ from what runs in
-- production, and the point of these shims is that the migrations are exercised
-- exactly as written.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON TABLES TO authenticated, anon, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON SEQUENCES TO authenticated, anon, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO authenticated, anon, service_role;

-- And for anything already created before this point.
GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated, anon, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO authenticated, anon, service_role;
