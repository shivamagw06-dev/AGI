-- Durable, research-only Nifty 200 conviction rankings. Computation stays on
-- the finance backend; the Intelligence Engine reads these precomputed rows.
create table if not exists public.evidence_conviction_runs (
  id uuid primary key default gen_random_uuid(),
  strategy text not null check (strategy = 'evidence_confirmed_conviction_v1'),
  universe text not null check (universe = 'nifty200'),
  generated_at timestamptz not null,
  universe_size integer not null check (universe_size between 0 and 200),
  methodology jsonb not null default '{}'::jsonb,
  counts jsonb not null default '{}'::jsonb,
  research_only boolean not null default true check (research_only),
  created_at timestamptz not null default now(),
  unique (strategy, generated_at)
);

create table if not exists public.evidence_conviction_rankings (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.evidence_conviction_runs(id) on delete cascade,
  symbol text not null,
  sector text,
  rank integer not null check (rank between 1 and 200),
  conviction_score numeric not null check (conviction_score between 0 and 100),
  conviction_label text not null check (conviction_label in ('HIGH_CONVICTION','CONFIRMED','WATCH','TACTICAL_ONLY','CONTRADICTED','INCOMPLETE')),
  evidence_coverage numeric not null check (evidence_coverage between 0 and 1),
  confluence_class text,
  market_regime text,
  eligible_for_research_shortlist boolean not null default false,
  thesis text not null,
  risk_note text not null,
  component_scores jsonb not null default '{}'::jsonb,
  evidence_snapshot jsonb not null default '{}'::jsonb,
  research_only boolean not null default true check (research_only),
  created_at timestamptz not null default now(),
  unique (run_id, symbol),
  unique (run_id, rank)
);

create index if not exists evidence_conviction_runs_time_idx on public.evidence_conviction_runs (generated_at desc);
create index if not exists evidence_conviction_rankings_run_rank_idx on public.evidence_conviction_rankings (run_id, rank);
create index if not exists evidence_conviction_rankings_symbol_idx on public.evidence_conviction_rankings (symbol, created_at desc);

alter table public.evidence_conviction_runs enable row level security;
alter table public.evidence_conviction_rankings enable row level security;

comment on table public.evidence_conviction_runs is 'Research-only Nifty 200 evidence-confirmed conviction runs.';
comment on table public.evidence_conviction_rankings is 'Precomputed conviction rankings for read-only consumption by Ask AGI and research UIs.';
