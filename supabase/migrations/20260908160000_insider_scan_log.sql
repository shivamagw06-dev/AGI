-- When each issuer's insider filings were last looked at.
--
-- The universe is roughly four thousand eight hundred held tickers, each with
-- its own stream of Form 4s. Without a record of what was scanned and when,
-- every run starts from the beginning: four thousand index requests before a
-- single document is read, most of them for issuers that have filed nothing.
--
-- The price backfill arrived at the same answer after three attempts at
-- inferring freshness from the rows it had written. Recording it directly is
-- both cheaper and able to represent the outcomes that write nothing - an
-- issuer with no filings, or one whose documents would not parse.
create table if not exists public.institutional_insider_scan_log (
  ticker text primary key,
  cik text,
  scanned_at timestamptz not null default now(),
  filings_seen integer not null default 0,
  filings_new integer not null default 0,
  filings_parsed integer not null default 0,
  status text not null,
  detail text
);

alter table public.institutional_insider_scan_log enable row level security;

-- Service role only, like the other collection tables. Nothing user-facing
-- reads this; the page reads institutional_external_filings.
revoke all on public.institutional_insider_scan_log from anon, authenticated;
