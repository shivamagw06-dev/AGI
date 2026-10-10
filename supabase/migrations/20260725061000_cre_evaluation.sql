-- Continuous Research Evaluation P0 persistence (WBS CRE-001–005)
-- Evaluation / scorecard schema only. Never writes production engine current tables.

create table if not exists public.cre_evaluation (
  evaluation_id text primary key,
  as_of date not null,
  dataset_id text not null,
  started_at timestamptz not null,
  finished_at timestamptz not null,
  replay_run_id text,
  engine_scorecards jsonb not null default '[]'::jsonb,
  composite jsonb,
  drift_alerts jsonb not null default '[]'::jsonb,
  regression_alerts jsonb not null default '[]'::jsonb,
  promotion jsonb,
  dashboard jsonb not null default '{}'::jsonb,
  production_influence boolean not null default false,
  flags jsonb not null default '{"CRE": true, "PROMOTION": false}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.cre_scorecard_latest (
  engine text primary key,
  as_of date not null,
  model_version text,
  formula_versions jsonb not null default '{}'::jsonb,
  rolling jsonb not null default '{}'::jsonb,
  rank_score double precision not null default 0,
  status text not null default 'ok',
  notes jsonb not null default '[]'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists cre_evaluation_started_idx
  on public.cre_evaluation (started_at desc);

create index if not exists cre_evaluation_as_of_idx
  on public.cre_evaluation (as_of desc);
