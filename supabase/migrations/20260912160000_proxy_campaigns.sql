-- Proxy contests: who a manager campaigned against, and when.
--
-- Of the fifty tracked managers, forty-four file nothing with the SEC but
-- position tables and stake declarations. The proxy contest is the exception.
-- A manager soliciting against a board must file what it sends to
-- shareholders, so Pershing Square's 162 campaign filings and Third Point's
-- 115 are public, indexed by CIK and fetchable on a schedule - the only
-- manager-authored writing anywhere in EDGAR.
--
-- No document text is stored here, deliberately. Those filings are the
-- managers' own words and their own copyright. What this keeps is the record
-- of the campaign - who filed against whom, on what date, under which form -
-- which is a fact about a public filing rather than a copy of one, and a
-- source_url so a reader who wants the argument reads it where it lives.
--
-- The subject comes from the filing header, not the document. EDGAR stamps
-- every solicitation with a SUBJECT COMPANY block naming the target and a
-- FILED BY block naming the filer. Both carry a COMPANY CONFORMED NAME field
-- and the subject appears first, which is the one thing a careless parser
-- gets wrong - it attributes every campaign to the company being campaigned
-- against.

create table if not exists public.institutional_proxy_filings (
  id uuid primary key default gen_random_uuid(),
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  accession_number text not null unique,
  form_type text not null,
  filed_at date,
  -- The company the campaign is against, as EDGAR names it.
  subject_cik text,
  subject_name text,
  source_url text not null,
  source_as_of timestamptz not null default now()
);

-- The question asked of this table is always "what has this manager
-- campaigned on", and second "who else went after this company".
create index if not exists institutional_proxy_filings_manager_idx
  on public.institutional_proxy_filings (manager_id, filed_at desc);
create index if not exists institutional_proxy_filings_subject_idx
  on public.institutional_proxy_filings (subject_cik, filed_at desc);

alter table public.institutional_proxy_filings enable row level security;
-- Not exposed to the anon key, like the holdings it sits beside. The page
-- reads it through the server.
revoke all on table public.institutional_proxy_filings from public, anon, authenticated;
grant select, insert, update, delete on table public.institutional_proxy_filings to service_role;

comment on table public.institutional_proxy_filings is
  'Proxy solicitations a tracked manager filed against a company board. Metadata and a link only - the documents are the managers own words and are not reproduced.';
