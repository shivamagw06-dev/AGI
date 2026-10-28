-- Financial statements as reported, one row per company per period.
--
-- Fifty-one of the hundred underwriting questions are arithmetic over these
-- line items across years, and none of them could be answered: AGI held one
-- snapshot per ticker carrying revenue, EBITDA, market cap and enterprise
-- value, and nothing of receivables, inventories, capex, debt or share count.
--
-- Imported from a structured file rather than parsed out of an annual report.
-- A table reader that guesses at footnotes, restatements and currencies is the
-- highest-fabrication-risk thing this codebase could contain, and a wrong
-- Net Debt/EBITDA is worse than a blank one.
--
-- Every figure is stored in the unit it was reported in, with the currency and
-- the scale beside it. A number whose scale is assumed is how a thousand-fold
-- error reaches a page.
create table if not exists public.company_financials (
  id uuid primary key default gen_random_uuid(),
  ticker text not null,
  -- The last day of the period, not the day it was filed.
  period_end date not null,
  -- 'annual' or 'quarter'. A quarter compared against a year is the kind of
  -- mistake a column of numbers makes easy and a reader never sees.
  period_type text not null check (period_type in ('annual', 'quarter')),
  -- 'consolidated' or 'standalone'. An Indian filer reports both and they are
  -- not comparable.
  basis text not null default 'consolidated' check (basis in ('consolidated', 'standalone')),
  currency text not null,
  -- What one unit in the columns below means: 1, 1000, 100000 (lakh),
  -- 1000000, 10000000 (crore). Stored rather than normalised, so the figure
  -- always reads back as it was reported.
  scale numeric not null default 1 check (scale > 0),
  -- Whether this period was restated by a later filing. A restated period
  -- compared against an as-first-reported one produces a growth rate neither
  -- filing ever claimed.
  restated boolean not null default false,

  -- Income statement
  revenue numeric,
  cost_of_sales numeric,
  gross_profit numeric,
  operating_expense numeric,
  ebitda numeric,
  ebit numeric,
  depreciation numeric,
  interest_expense numeric,
  pre_tax_income numeric,
  tax_expense numeric,
  net_income numeric,
  share_based_comp numeric,

  -- Balance sheet
  cash numeric,
  receivables numeric,
  inventories numeric,
  payables numeric,
  gross_debt numeric,
  total_equity numeric,
  invested_capital numeric,

  -- Cash flow
  operating_cash_flow numeric,
  capex numeric,
  acquisitions numeric,
  dividends numeric,
  buybacks numeric,
  shares_issued numeric,

  -- Share count, diluted weighted average, in the same scale as above.
  share_count numeric,

  source_file text,
  imported_at timestamptz not null default now(),
  -- One row per company per period per basis. A re-import of the same file
  -- updates rather than accumulating a second reading of the same year.
  unique (ticker, period_end, period_type, basis)
);

create index if not exists company_financials_ticker_period_idx
  on public.company_financials (ticker, period_end desc);

alter table public.company_financials enable row level security;
revoke all on table public.company_financials from public, anon, authenticated;
grant select, insert, update, delete on table public.company_financials to service_role;

comment on table public.company_financials is
  'Financial statements as reported, one row per company per period. Imported from a structured file, never parsed out of a document. Currency and scale are stored beside every figure.';
