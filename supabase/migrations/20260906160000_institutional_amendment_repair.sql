-- Repairing amendments already ingested wrongly.
--
-- Every 13F-HR/A ingested before the classification was fixed took the merge
-- branch, because the parser searched for a tag SEC does not emit against a
-- document that was never downloaded. A restatement that removed a position
-- therefore left it in the portfolio, and those phantom positions are still in
-- institutional_holdings today, feeding consensus, sector weights and anything
-- else that reads them.
--
-- The repair re-ingests each affected quarter from EDGAR. That overwrites rows,
-- so the state before the repair is archived first. Two reasons: a repair that
-- turns out to be wrong must be reversible, and a client asking why a position
-- disappeared is entitled to an answer better than "the data changed".

create table if not exists public.institutional_holdings_archive (
  id uuid primary key default gen_random_uuid(),
  -- Which repair run captured this. Not a foreign key: the archive must outlive
  -- any pruning of the run table, since it is the audit record.
  repair_run_id uuid,
  filing_id uuid,
  accession_number text,
  manager_id uuid,
  report_date date,
  archived_at timestamptz not null default now(),
  reason text not null default 'amendment_repair',
  -- The row exactly as it stood, not a normalised projection of it. A schema
  -- change later must not make the archive unreadable.
  holding jsonb not null
);

create index if not exists institutional_holdings_archive_filing_idx
  on public.institutional_holdings_archive (filing_id);
create index if not exists institutional_holdings_archive_run_idx
  on public.institutional_holdings_archive (repair_run_id, archived_at desc);

-- The reconciliation report, one row per filing considered.
--
-- Filings that needed no change are recorded too. "We looked at 47 amendments,
-- 12 were wrong" is a different statement from "12 amendments were wrong", and
-- only the first is verifiable.
create table if not exists public.institutional_amendment_repairs (
  id uuid primary key default gen_random_uuid(),
  repair_run_id uuid not null,
  filing_id uuid,
  accession_number text not null,
  manager_slug text,
  report_date date,

  -- What it was recorded as, and what SEC actually says.
  previous_amendment_type text,
  resolved_amendment_type text,
  reclassified boolean not null default false,

  -- What the repair did to the holdings.
  positions_before integer,
  positions_after integer,
  positions_removed integer not null default 0,
  positions_retained integer not null default 0,
  -- The identifiers actually removed, so a removal can be checked rather than
  -- taken on trust.
  removed_positions jsonb not null default '[]'::jsonb,

  outcome text not null
    check (outcome in ('repaired', 'unchanged', 'needs_review', 'failed', 'would_repair')),
  needs_review boolean not null default false,
  error text,

  applied boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists institutional_amendment_repairs_run_idx
  on public.institutional_amendment_repairs (repair_run_id, created_at desc);
create index if not exists institutional_amendment_repairs_outcome_idx
  on public.institutional_amendment_repairs (outcome, created_at desc);

-- One row per repair run, so a report can be read back whole.
create or replace view public.institutional_amendment_repair_summary
with (security_invoker = true) as
select
  repair_run_id,
  bool_and(applied) as applied,
  min(created_at) as started_at,
  max(created_at) as finished_at,
  count(*)::int as filings_examined,
  count(*) filter (where reclassified)::int as filings_reclassified,
  count(*) filter (where outcome = 'repaired')::int as filings_repaired,
  count(*) filter (where outcome = 'would_repair')::int as filings_would_repair,
  count(*) filter (where outcome = 'unchanged')::int as filings_unchanged,
  count(*) filter (where outcome = 'needs_review')::int as filings_needing_review,
  count(*) filter (where outcome = 'failed')::int as filings_failed,
  coalesce(sum(positions_removed), 0)::int as positions_removed,
  coalesce(sum(positions_retained), 0)::int as positions_retained
from public.institutional_amendment_repairs
group by repair_run_id;

alter table public.institutional_holdings_archive enable row level security;
alter table public.institutional_amendment_repairs enable row level security;

revoke all on table public.institutional_holdings_archive,
  public.institutional_amendment_repairs from anon, authenticated;
grant all on table public.institutional_holdings_archive,
  public.institutional_amendment_repairs to service_role;
revoke all on public.institutional_amendment_repair_summary from anon, authenticated;
grant select on public.institutional_amendment_repair_summary to service_role;
