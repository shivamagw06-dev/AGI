-- AGI Analyst Workspace (AWS) P0
-- Aggregation workspace metadata only. No new research engines.

create table if not exists public.aws_workspace_sessions (
  session_id text primary key,
  workspace text not null,
  ticker text,
  theme_id text,
  sector_id text,
  research_id text,
  as_of date,
  actor text not null default '',
  context jsonb not null default '{}'::jsonb,
  aws_version text not null default 'aws-v1.0.1',
  created_at timestamptz not null default now()
);

create index if not exists aws_workspace_sessions_workspace_idx
  on public.aws_workspace_sessions (workspace, created_at desc);
