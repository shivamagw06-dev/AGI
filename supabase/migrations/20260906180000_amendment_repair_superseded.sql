-- Divested positions and restated rows are not the same thing.
--
-- filingKey is cusip|class|shareType|putCall and carries no value or share
-- count, so when a restatement re-reports a security with corrected figures the
-- old row disappears and a new one takes its place. At row level that is
-- indistinguishable from a position being sold.
--
-- The distinction is not cosmetic. H&H International's Q4-2024 restatement
-- reported APPLE, BERKSHIRE, ALPHABET, PDD and OCCIDENTAL as removed when all
-- five are in the amendment SEC actually filed. Read literally, the audit
-- record said the manager exited Apple. It did not - the row was restated.
--
-- positions_removed keeps its meaning and now counts only securities absent
-- from the result entirely. This column carries the rest.

alter table public.institutional_amendment_repairs
  add column if not exists positions_superseded integer not null default 0;

comment on column public.institutional_amendment_repairs.positions_removed is
  'Securities no longer held at all after the repair - a genuine divestment.';
comment on column public.institutional_amendment_repairs.positions_superseded is
  'Rows replaced by a restated version of the same security. The position is still held; only its figures changed.';

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
  coalesce(sum(positions_superseded), 0)::int as positions_superseded,
  coalesce(sum(positions_retained), 0)::int as positions_retained
from public.institutional_amendment_repairs
group by repair_run_id;

revoke all on public.institutional_amendment_repair_summary from anon, authenticated;
grant select on public.institutional_amendment_repair_summary to service_role;
