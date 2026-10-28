-- Investment Operations Centre (IOC) P0
-- Monitoring metadata only. No research / trading / portfolio logic.

create table if not exists public.ioc_alerts (
  alert_id text primary key,
  kind text not null,
  severity text not null,
  component text not null,
  message text not null,
  status text,
  details jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create index if not exists ioc_alerts_active_idx
  on public.ioc_alerts (active, created_at desc);

create table if not exists public.ioc_reports (
  report_id text primary key,
  report_type text not null,
  title text not null,
  overall_status text not null,
  summary text not null default '',
  sections jsonb not null default '{}'::jsonb,
  ioc_version text not null default 'ioc-v1.0.1',
  generated_at timestamptz not null default now()
);

create index if not exists ioc_reports_type_idx
  on public.ioc_reports (report_type, generated_at desc);
