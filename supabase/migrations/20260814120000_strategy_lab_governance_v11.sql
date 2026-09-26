-- AGI Strategy Lab governance v1.1.
-- Existing records are mapped conservatively; this migration never promotes a strategy.

update public.strategy_lab_strategies
set lifecycle = case lifecycle
  when 'BACKTESTING' then 'IMPLEMENTED'
  when 'VALIDATING' then 'BACKTESTABLE'
  when 'PAPER' then 'PAPER_ELIGIBLE'
  when 'OPERATIONAL' then 'RESEARCH_VALIDATED'
  else lifecycle
end;

alter table public.strategy_lab_strategies
  drop constraint if exists strategy_lab_strategies_lifecycle_check;

alter table public.strategy_lab_strategies
  add constraint strategy_lab_strategies_lifecycle_check check (lifecycle in (
    'DRAFT','IMPLEMENTED','DATA_VALIDATED','BACKTESTABLE','RESEARCH_VALIDATED',
    'PAPER_ELIGIBLE','PAPER_VALIDATED','PRODUCTION_CANDIDATE',
    'EXECUTION_ELIGIBLE','SUSPENDED','RETIRED'
  ));

update public.strategy_lab_signals
set eligibility = case eligibility
  when 'RESEARCH_ONLY' then 'RESEARCH_ONLY'
  when 'BACKTESTED' then 'RESEARCH_ONLY'
  when 'VALIDATED' then 'RESEARCH_ONLY'
  when 'PAPER' then 'PAPER_ELIGIBLE'
  when 'TRADE_ELIGIBLE' then 'BLOCKED'
  when 'SUSPENDED' then 'BLOCKED'
  else 'BLOCKED'
end;

alter table public.strategy_lab_signals
  alter column eligibility set default 'BLOCKED',
  drop constraint if exists strategy_lab_signals_eligibility_check;

alter table public.strategy_lab_signals
  add constraint strategy_lab_signals_eligibility_check check (eligibility in (
    'RESEARCH_ONLY','BLOCKED','PAPER_ELIGIBLE','EXECUTION_ELIGIBLE'
  ));

alter table public.strategy_lab_signals
  add column if not exists signal_session date,
  add column if not exists research_direction text,
  add column if not exists signal_strength numeric,
  add column if not exists prices jsonb not null default '{}'::jsonb,
  add column if not exists validation jsonb not null default '{}'::jsonb,
  add column if not exists governance jsonb not null default '{}'::jsonb;

alter table public.strategy_lab_versions
  add column if not exists formula_hash text,
  add column if not exists data_version text,
  add column if not exists validation_state jsonb not null default '{}'::jsonb;

create index if not exists strategy_lab_signals_session_idx
  on public.strategy_lab_signals(signal_session desc, ticker);

