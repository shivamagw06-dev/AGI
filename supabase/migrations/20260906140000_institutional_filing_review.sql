-- Amendments that could not be classified.
--
-- A 13F-HR/A either restates the earlier report or adds to it, and the two
-- demand opposite handling. Guessing wrong in one direction leaves positions
-- the manager removed sitting in the portfolio; guessing wrong in the other
-- deletes every position the amendment does not mention - which for an
-- expired-confidential-treatment filing is nearly the whole portfolio.
--
-- So an amendment whose cover page cannot be read is recorded and escalated
-- rather than applied. These two columns are where that escalation lives: the
-- filing is stored, is_active stays false so the earlier version remains
-- authoritative, and an operator resolves it.

alter table public.institutional_filings
  add column if not exists needs_review boolean not null default false,
  add column if not exists review_reason text;

-- Partial, because the answer is almost always zero rows and that is the query
-- the operations panel runs.
create index if not exists institutional_filings_needs_review_idx
  on public.institutional_filings (manager_id, report_date)
  where needs_review;

comment on column public.institutional_filings.needs_review is
  'Set when an amendment could not be classified from its SEC cover page. The filing is recorded but not applied; is_active stays false so the prior version remains authoritative.';
comment on column public.institutional_filings.review_reason is
  'Human-readable reason the amendment could not be classified, quoted back from the cover page where possible.';
