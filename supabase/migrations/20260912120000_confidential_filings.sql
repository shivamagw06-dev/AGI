-- Filings whose information table was withheld under confidential treatment.
--
-- Norges Bank files a schema-valid placeholder on the due date - one row,
-- issuer "NA", CUSIP 000000000, zero value, zero shares - and files the real
-- holdings as a 13F-HR/A a year later when the confidentiality lapses. That
-- placeholder was being stored as a position, so two quarters read as
-- one-name books against a median of 2,108 and the quarter that followed
-- read as 100% turnover.
--
-- The cover page declared the truth the whole time. Q1 2026 states 1,507
-- entries worth $864,690,921,985 with isConfidentialOmitted true; Q3 2025
-- states 1,516 worth $870,104,905,340. Those numbers are what these columns
-- keep, so a withheld quarter can say what it is holding back instead of
-- appearing as a manager that liquidated.
--
-- is_active stays false on these rows. There are no holdings to serve, and a
-- quarter absent from the series is honest in a way that a one-position book
-- is not.

alter table public.institutional_filings
  add column if not exists confidential_omitted boolean not null default false,
  add column if not exists declared_holdings_count integer,
  add column if not exists declared_value_usd numeric;

comment on column public.institutional_filings.confidential_omitted is
  'The filer''s <isConfidentialOmitted> flag. True on a filing that withholds positions under a confidential treatment request - which is usually partial (Berkshire Q1 2025 withheld four of a disclosed 110) and occasionally total (Norges Bank withholds the entire table). Holdings presence, not this flag, says which.';
comment on column public.institutional_filings.declared_holdings_count is
  'The cover page''s <tableEntryTotal>: how many entries the filer says the information table contains. Compared against what was parsed, this is what makes a table that failed to read a loud error rather than a silently small portfolio.';
comment on column public.institutional_filings.declared_value_usd is
  'The cover page''s <tableValueTotal>. Retained for withheld filings so the reported size of a quarter survives even when its positions do not.';

-- Withheld quarters are the ones an operator asks after, and they are rare.
create index if not exists institutional_filings_confidential_idx
  on public.institutional_filings (manager_id, report_date)
  where confidential_omitted and not is_active;
