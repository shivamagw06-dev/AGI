-- ORCH control plane ledger (Architecture v1.0.1 / WBS ORCH-001)
-- Document ID: ORCH — not E00 Layer 5 (E10 Portfolio Construction).
-- Research-only infrastructure; no order execution.

create table if not exists public.orch_dag_versions (
  dag_version text primary key,
  spec_hash text not null,
  created_at timestamptz not null default now(),
  is_active boolean not null default false
);

create table if not exists public.orch_dag_nodes (
  dag_version text not null references public.orch_dag_versions (dag_version),
  node_id text not null,
  layer text not null,
  engine text,
  max_concurrency int not null default 1,
  soft_timeout_ms int not null,
  hard_timeout_ms int not null,
  primary key (dag_version, node_id)
);

create table if not exists public.orch_dag_edges (
  dag_version text not null,
  parent_node text not null,
  child_node text not null,
  dependency_type text not null check (dependency_type in ('blocking', 'optional', 'shadow')),
  primary key (dag_version, parent_node, child_node)
);

create table if not exists public.orch_runs (
  run_id uuid primary key,
  run_kind text not null,
  dag_version text not null references public.orch_dag_versions (dag_version),
  as_of date,
  status text not null,
  started_at timestamptz not null,
  finished_at timestamptz,
  trigger_reason text,
  parent_run_id uuid references public.orch_runs (run_id)
);

create index if not exists orch_runs_kind_started_idx
  on public.orch_runs (run_kind, started_at desc);

create table if not exists public.orch_run_nodes (
  run_id uuid not null references public.orch_runs (run_id),
  node_id text not null,
  status text not null,
  attempt int not null default 1,
  latency_ms int,
  input_hash text,
  output_hash text,
  error_code text,
  detail jsonb not null default '{}'::jsonb,
  primary key (run_id, node_id, attempt)
);

create table if not exists public.orch_snapshots (
  snapshot_id text primary key,
  as_of date not null,
  dag_version text not null references public.orch_dag_versions (dag_version),
  engine_hashes jsonb not null,
  weight_set_id text,
  feature_registry_version text,
  created_at timestamptz not null default now()
);

create table if not exists public.orch_feature_flags (
  flag_key text primary key,
  flag_value jsonb not null,
  updated_at timestamptz not null default now(),
  updated_by text not null
);

create table if not exists public.orch_feature_flag_audit (
  id bigserial primary key,
  flag_key text not null,
  old_value jsonb,
  new_value jsonb not null,
  changed_at timestamptz not null default now(),
  changed_by text not null
);

-- Seed active DAG version row (graph content loaded from app/orch/dag/orch-1.0.0.json by workers).
insert into public.orch_dag_versions (dag_version, spec_hash, is_active)
values ('orch-1.0.0', 'pending_app_hash', true)
on conflict (dag_version) do nothing;

-- Safe defaults for Architecture v1.0.1 migration modes (M0 incumbent).
insert into public.orch_feature_flags (flag_key, flag_value, updated_by)
values
  ('e03_production_primary', 'true'::jsonb, 'wbs-orch-001'),
  ('e10_views_source', '"e03"'::jsonb, 'wbs-orch-001'),
  ('l4_shadow_write', 'false'::jsonb, 'wbs-orch-001'),
  ('l4_replace_e03_display', 'false'::jsonb, 'wbs-orch-001'),
  ('l4_cio_brief_primary', 'false'::jsonb, 'wbs-orch-001'),
  ('e14_enforce_promote', 'true'::jsonb, 'wbs-orch-001')
on conflict (flag_key) do nothing;
