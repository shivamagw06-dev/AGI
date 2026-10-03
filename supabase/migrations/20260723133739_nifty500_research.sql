-- Public, derived Nifty 500 research snapshots.
-- Raw market data must never be stored or returned through these tables.

create table if not exists public.nifty500_research_runs (
  id uuid primary key default gen_random_uuid(),
  generated_at timestamptz not null default now(),
  run_name text not null,
  total_stocks_analyzed integer not null default 0 check (total_stocks_analyzed >= 0),
  rejected_symbols jsonb not null default '[]'::jsonb,
  disclaimer text not null,
  status text not null default 'draft' check (status in ('draft', 'published', 'failed')),
  is_current boolean not null default false,
  published_at timestamptz,
  created_at timestamptz not null default now()
);

create unique index if not exists nifty500_research_one_current_run
  on public.nifty500_research_runs (is_current)
  where is_current;

create index if not exists nifty500_research_runs_published_at_idx
  on public.nifty500_research_runs (published_at desc)
  where status = 'published';

create table if not exists public.nifty500_stock_research (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.nifty500_research_runs(id) on delete cascade,
  symbol text not null check (symbol = upper(symbol)),
  overall_sentiment text not null check (
    overall_sentiment in ('Strong Bullish', 'Bullish', 'Neutral', 'Bearish', 'Strong Bearish')
  ),
  agi_research_score numeric(5,1) not null check (agi_research_score between 0 and 100),
  ai_confidence_percent smallint not null check (ai_confidence_percent between 0 and 100),
  research_summary text not null,
  trend_analysis text not null,
  momentum_analysis text not null,
  volume_analysis text not null,
  volatility_analysis text not null,
  market_structure_analysis text not null,
  relative_strength_analysis text not null,
  supporting_factors jsonb not null default '[]'::jsonb,
  risk_factors jsonb not null default '[]'::jsonb,
  key_observations jsonb not null default '[]'::jsonb,
  last_updated timestamptz not null,
  created_at timestamptz not null default now(),
  unique (run_id, symbol)
);

create index if not exists nifty500_stock_research_run_score_idx
  on public.nifty500_stock_research (run_id, agi_research_score desc);

create index if not exists nifty500_stock_research_run_sentiment_score_idx
  on public.nifty500_stock_research (run_id, overall_sentiment, agi_research_score desc);

create index if not exists nifty500_stock_research_symbol_idx
  on public.nifty500_stock_research (symbol);

alter table public.nifty500_research_runs enable row level security;
alter table public.nifty500_stock_research enable row level security;

create policy "Published Nifty 500 runs are publicly readable"
  on public.nifty500_research_runs
  for select
  to anon, authenticated
  using (status = 'published' and is_current);

create policy "Published Nifty 500 records are publicly readable"
  on public.nifty500_stock_research
  for select
  to anon, authenticated
  using (
    exists (
      select 1
      from public.nifty500_research_runs run
      where run.id = nifty500_stock_research.run_id
        and run.status = 'published'
        and run.is_current
    )
  );

-- The server-side publisher creates a fully populated draft, clears the
-- previous current run, then marks this run current. Because stock records are
-- written before either update, a partial run is never exposed publicly.
