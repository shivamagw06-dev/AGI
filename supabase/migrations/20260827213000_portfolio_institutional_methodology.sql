-- Institutional methodology and provenance foundations for Portfolio Intelligence.
-- This migration does not infer a benchmark or rewrite historical analytics.

alter table if exists public.client_portfolios
  alter column benchmark_components set default '[]'::jsonb;

alter table if exists public.client_portfolios
  add column if not exists benchmark_policy jsonb not null default '{"mode":"unassigned"}'::jsonb;

alter table if exists public.client_portfolio_snapshots
  add column if not exists methodology_version text,
  add column if not exists metric_eligibility jsonb not null default '{}'::jsonb,
  add column if not exists source_provenance jsonb not null default '{}'::jsonb;

create table if not exists public.portfolio_methodology_versions (
  version text primary key,
  status text not null check (status in ('active', 'retired', 'draft')),
  effective_from timestamptz not null,
  metric_requirements jsonb not null default '{}'::jsonb,
  notes text,
  created_at timestamptz not null default now()
);

insert into public.portfolio_methodology_versions (
  version, status, effective_from, metric_requirements, notes
) values (
  'agi-portfolio-methodology-v2',
  'active',
  now(),
  '{
    "twr":{"portfolioObservations":2},
    "xirr":{"transactions":1,"elapsedDays":30},
    "annualizedReturn":{"returnObservations":60},
    "volatility":{"returnObservations":60},
    "sharpe":{"returnObservations":60},
    "sortino":{"returnObservations":60},
    "maxDrawdown":{"returnObservations":20},
    "beta":{"alignedBenchmarkObservations":60},
    "alpha":{"alignedBenchmarkObservations":60},
    "trackingError":{"alignedBenchmarkObservations":60},
    "informationRatio":{"alignedBenchmarkObservations":60},
    "var95":{"returnObservations":60},
    "expectedShortfall95":{"returnObservations":60},
    "correlation":{"alignedBenchmarkObservations":30}
  }'::jsonb,
  'Fail-closed institutional portfolio methodology. Missing observations produce not_available, never zero.'
)
on conflict (version) do update set
  status = excluded.status,
  metric_requirements = excluded.metric_requirements,
  notes = excluded.notes;

create table if not exists public.portfolio_research_impacts (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  holding_id uuid references public.client_portfolio_holdings(id) on delete set null,
  event_key text not null,
  event_type text not null,
  impact_type text not null,
  direction text check (direction is null or direction in ('positive', 'negative', 'mixed', 'neutral')),
  confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 100)),
  status text not null default 'evidence_only' check (status in ('evidence_only', 'classified', 'reviewed', 'dismissed')),
  title text,
  occurred_at timestamptz,
  evidence jsonb not null default '{}'::jsonb,
  provenance jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique nulls not distinct (portfolio_id, event_key, holding_id)
);

create index if not exists portfolio_research_impacts_portfolio_occurred_idx
  on public.portfolio_research_impacts (portfolio_id, occurred_at desc);
create index if not exists portfolio_research_impacts_user_status_idx
  on public.portfolio_research_impacts (user_id, status, updated_at desc);

alter table public.portfolio_methodology_versions enable row level security;
alter table public.portfolio_research_impacts enable row level security;

drop policy if exists "Authenticated users can read portfolio methodology" on public.portfolio_methodology_versions;
create policy "Authenticated users can read portfolio methodology"
  on public.portfolio_methodology_versions for select to authenticated
  using (true);

drop policy if exists "Users can read own portfolio research impacts" on public.portfolio_research_impacts;
create policy "Users can read own portfolio research impacts"
  on public.portfolio_research_impacts for select to authenticated
  using (auth.uid() = user_id);

drop policy if exists "Users can insert own portfolio research impacts" on public.portfolio_research_impacts;
create policy "Users can insert own portfolio research impacts"
  on public.portfolio_research_impacts for insert to authenticated
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.client_portfolios portfolio
      where portfolio.id = portfolio_id and portfolio.user_id = (select auth.uid())
    )
  );

drop policy if exists "Users can update own portfolio research impacts" on public.portfolio_research_impacts;
create policy "Users can update own portfolio research impacts"
  on public.portfolio_research_impacts for update to authenticated
  using (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.client_portfolios portfolio
      where portfolio.id = portfolio_id and portfolio.user_id = (select auth.uid())
    )
  )
  with check (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.client_portfolios portfolio
      where portfolio.id = portfolio_id and portfolio.user_id = (select auth.uid())
    )
  );

drop policy if exists "Users can delete own portfolio research impacts" on public.portfolio_research_impacts;
create policy "Users can delete own portfolio research impacts"
  on public.portfolio_research_impacts for delete to authenticated
  using (
    (select auth.uid()) = user_id
    and exists (
      select 1 from public.client_portfolios portfolio
      where portfolio.id = portfolio_id and portfolio.user_id = (select auth.uid())
    )
  );

revoke all on table public.portfolio_methodology_versions from anon;
revoke all on table public.portfolio_research_impacts from anon;
grant select on table public.portfolio_methodology_versions to authenticated;
grant select, insert, update, delete on table public.portfolio_research_impacts to authenticated;

comment on column public.client_portfolios.benchmark_policy is
  'Benchmark is unavailable unless mode is explicitly set to explicit by the portfolio owner.';
comment on table public.portfolio_research_impacts is
  'Evidence-backed research, filing, corporate-action and macro impacts mapped to owned portfolio holdings.';
