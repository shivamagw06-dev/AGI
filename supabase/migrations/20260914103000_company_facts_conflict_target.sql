-- The identity index has to be usable as an upsert target.
--
-- company_facts_identity_idx is declared over coalesce(segment, '') and
-- coalesce(geography, ''). Postgres infers an ON CONFLICT target by matching
-- the inference clause against an index, and an expression index can only be
-- matched by repeating the expression. PostgREST's on_conflict parameter takes
-- a list of column names and cannot express one, so every upsert against this
-- table fails to infer the index - which means re-reading a document either
-- errors or inserts a second copy of every fact in it.
--
-- The fix is to hold "no segment" as '' rather than as NULL, so the index is
-- over plain columns. That is a real change of meaning and worth being
-- explicit about: for this table NULL never meant "unknown segment", it meant
-- "this figure is not segmental", and '' says the same thing in a form the
-- index can use.
update public.company_facts set segment = '' where segment is null;
update public.company_facts set geography = '' where geography is null;

alter table public.company_facts
  alter column segment set default '',
  alter column segment set not null,
  alter column geography set default '',
  alter column geography set not null;

drop index if exists public.company_facts_identity_idx;

create unique index if not exists company_facts_identity_idx
  on public.company_facts (company, period_end, period_type, accounting_scope, entity_scope,
    concept, definition_id, segment, geography, dimensions, reported_in_document);

comment on column public.company_facts.segment is
  'The reporting segment, or the empty string for a figure that is not segmental. Never NULL: the identity index is an upsert target and must be over plain columns.';
