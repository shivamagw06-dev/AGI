-- What a ticker meant, and when.
--
-- The SEC's company_tickers.json lists companies that are registered now. It
-- is sound - every control name is in it - but it cannot answer a question
-- about the past, and a decade of 13F holdings is mostly questions about the
-- past. Activision, Pioneer, Seagen, Splunk, WestRock, Marathon Oil, Discover
-- and Electronic Arts have all left it, and 191 venue-coded holdings worth
-- $1.48tn are refused because no live registry can confirm a ticker that no
-- longer exists.
--
-- The SEC's bulk Form 345 datasets do carry it. Every quarterly SUBMISSION.tsv
-- names the issuer, its CIK and its trading symbol as filed, for every issuer
-- that quarter - so the union across quarters is a record of what each ticker
-- meant while it meant it.
--
-- Small: a few thousand distinct triples per quarter, and heavily repeated
-- between them.
create table if not exists public.sec_issuer_tickers (
  cik text not null,
  ticker text not null,
  issuer_name text not null,
  -- The window over which the SEC saw this issuer filing under this symbol.
  -- A ticker that changes hands produces two rows with disjoint windows, which
  -- is the fact the caller needs: PARA was Paramount Global and is now Banzai
  -- International, and a 2019 holding must resolve to the first.
  first_seen date not null,
  last_seen date not null,
  filings integer not null default 0,
  refreshed_at timestamptz not null default now(),
  primary key (ticker, cik)
);

create index if not exists sec_issuer_tickers_ticker_idx
  on public.sec_issuer_tickers (ticker);

alter table public.sec_issuer_tickers enable row level security;

comment on table public.sec_issuer_tickers is
  'Ticker to issuer, as filed on Form 3/4/5, with the window each pair was observed. Built from the SEC bulk Form 345 datasets; includes issuers that have since delisted.';
