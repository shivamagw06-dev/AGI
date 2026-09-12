-- AGI Phase 2: authoritative strategy Validation Registry.
-- Models and scanners may write evidence, but only registry decisions govern
-- lifecycle claims, allowed use, health, and execution eligibility.

create table if not exists public.strategy_validation_registry (
  strategy_key text primary key,
  strategy_name text not null,
  strategy_version text not null,
  requested_lifecycle text not null default 'EXPERIMENTAL',
  supported_lifecycle text not null default 'EXPERIMENTAL',
  effective_lifecycle text not null default 'EXPERIMENTAL',
  current_health text not null default 'DEGRADED',
  health_reason text,
  allowed_use text not null default 'Research only',
  execution_status text not null default 'BLOCKED',
  historical_claims_allowed boolean not null default false,
  automatic_demotion boolean not null default true,
  registry_version text not null,
  decision jsonb not null default '{}'::jsonb,
  evaluated_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (requested_lifecycle in ('EXPERIMENTAL','OPERATIONAL','BACKTESTABLE','RESEARCH_VALIDATED','INVESTMENT_VALIDATED','PRODUCTION_CANDIDATE','PRODUCTION')),
  check (supported_lifecycle in ('EXPERIMENTAL','OPERATIONAL','BACKTESTABLE','RESEARCH_VALIDATED','INVESTMENT_VALIDATED','PRODUCTION_CANDIDATE','PRODUCTION')),
  check (effective_lifecycle in ('EXPERIMENTAL','OPERATIONAL','BACKTESTABLE','RESEARCH_VALIDATED','INVESTMENT_VALIDATED','PRODUCTION_CANDIDATE','PRODUCTION')),
  check (current_health in ('HEALTHY','DEGRADED','STALE','SUSPENDED','FAILED')),
  check (execution_status in ('ALLOWED','BLOCKED'))
);

create table if not exists public.strategy_validation_evidence (
  id bigint generated always as identity primary key,
  strategy_key text not null references public.strategy_validation_registry(strategy_key),
  strategy_version text not null,
  gate_key text not null,
  status text not null,
  observed_at timestamptz,
  source text,
  source_version text,
  receipt_id text,
  metrics jsonb not null default '{}'::jsonb,
  limitations jsonb not null default '[]'::jsonb,
  evidence_hash text,
  recorded_at timestamptz not null default now(),
  check (gate_key in ('implementation','data_freshness','data_completeness','point_in_time','corporate_actions','backtest','out_of_sample','transaction_costs','liquidity_capacity','risk','walk_forward_paper','operational_controls')),
  check (status in ('PASSED','PARTIAL','FAILED','MISSING','NOT_APPLICABLE'))
);

create index if not exists strategy_validation_evidence_lookup_idx
  on public.strategy_validation_evidence(strategy_key, strategy_version, gate_key, recorded_at desc);

alter table public.strategy_validation_registry enable row level security;
alter table public.strategy_validation_evidence enable row level security;

create or replace function public.prevent_strategy_validation_evidence_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'strategy_validation_evidence is append-only';
end;
$$;

drop trigger if exists strategy_validation_evidence_append_only
  on public.strategy_validation_evidence;
create trigger strategy_validation_evidence_append_only
before update or delete on public.strategy_validation_evidence
for each row execute function public.prevent_strategy_validation_evidence_mutation();
