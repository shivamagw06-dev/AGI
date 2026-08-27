-- Evidence-aware institutional portfolio decision layer.
-- Stores client-approved policy, dated analytics and active exceptions.

create table if not exists public.client_portfolio_policies (
  portfolio_id uuid primary key references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  policy_name text not null default 'Client strategic allocation',
  base_currency text not null default 'INR' check (base_currency in ('INR', 'USD')),
  asset_targets jsonb not null default '{}'::jsonb,
  country_limits jsonb not null default '{}'::jsonb,
  sector_limits jsonb not null default '{}'::jsonb,
  currency_limits jsonb not null default '{}'::jsonb,
  max_position_pct numeric check (max_position_pct > 0 and max_position_pct <= 100),
  min_cash_pct numeric check (min_cash_pct >= 0 and min_cash_pct <= 100),
  max_cash_pct numeric check (max_cash_pct >= 0 and max_cash_pct <= 100),
  rebalance_tolerance_pct numeric not null default 5 check (rebalance_tolerance_pct > 0 and rebalance_tolerance_pct <= 50),
  risk_profile text,
  investment_horizon_years numeric check (investment_horizon_years > 0),
  approved_at timestamptz,
  approved_by uuid references auth.users(id) on delete set null,
  methodology_version text not null default 'agi-policy-v1',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.client_portfolio_institutional_reports (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  report_date date not null default current_date,
  engine_version text not null,
  evidence_grade text not null check (evidence_grade in ('A', 'B', 'C', 'D', 'E')),
  evidence_score numeric not null check (evidence_score >= 0 and evidence_score <= 100),
  report jsonb not null,
  generated_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (portfolio_id, report_date, engine_version)
);

create table if not exists public.client_portfolio_alerts (
  id uuid primary key default gen_random_uuid(),
  portfolio_id uuid not null references public.client_portfolios(id) on delete cascade,
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  alert_key text not null,
  severity text not null check (severity in ('info', 'watch', 'high')),
  title text not null,
  detail text,
  evidence jsonb not null default '{}'::jsonb,
  active boolean not null default true,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  resolved_at timestamptz,
  unique (portfolio_id, alert_key)
);

create index if not exists client_portfolio_reports_owner_idx
  on public.client_portfolio_institutional_reports (user_id, portfolio_id, report_date desc);
create index if not exists client_portfolio_alerts_owner_idx
  on public.client_portfolio_alerts (user_id, portfolio_id, active, severity);

alter table public.client_portfolio_policies enable row level security;
alter table public.client_portfolio_institutional_reports enable row level security;
alter table public.client_portfolio_alerts enable row level security;

revoke all on table public.client_portfolio_policies,
  public.client_portfolio_institutional_reports,
  public.client_portfolio_alerts from anon, authenticated;

grant select, insert, update, delete on table public.client_portfolio_policies to authenticated;
grant select, insert, update on table public.client_portfolio_institutional_reports to authenticated;
grant select, insert, update on table public.client_portfolio_alerts to authenticated;

create policy "Clients read their portfolio policy"
  on public.client_portfolio_policies for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "Clients create their portfolio policy"
  on public.client_portfolio_policies for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "Clients update their portfolio policy"
  on public.client_portfolio_policies for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);
create policy "Clients delete their portfolio policy"
  on public.client_portfolio_policies for delete to authenticated
  using ((select auth.uid()) = user_id);

create policy "Clients read their institutional reports"
  on public.client_portfolio_institutional_reports for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "Clients create their institutional reports"
  on public.client_portfolio_institutional_reports for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "Clients update their institutional reports"
  on public.client_portfolio_institutional_reports for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create policy "Clients read their portfolio alerts"
  on public.client_portfolio_alerts for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "Clients create their portfolio alerts"
  on public.client_portfolio_alerts for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "Clients update their portfolio alerts"
  on public.client_portfolio_alerts for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create or replace function public.sync_client_portfolio_institutional_report(
  p_portfolio_id uuid,
  p_engine_version text,
  p_report jsonb,
  p_alerts jsonb default '[]'::jsonb
) returns void
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_user_id uuid := (select auth.uid());
  v_generated_at timestamptz := coalesce((p_report ->> 'generatedAt')::timestamptz, now());
begin
  if v_user_id is null or not exists (
    select 1 from public.client_portfolios
    where id = p_portfolio_id and user_id = v_user_id
  ) then
    raise exception 'Portfolio access denied';
  end if;

  insert into public.client_portfolio_institutional_reports (
    portfolio_id, user_id, report_date, engine_version, evidence_grade,
    evidence_score, report, generated_at, updated_at
  ) values (
    p_portfolio_id, v_user_id, v_generated_at::date, p_engine_version,
    p_report #>> '{coverage,grade}',
    (p_report #>> '{coverage,score}')::numeric,
    p_report, v_generated_at, now()
  )
  on conflict (portfolio_id, report_date, engine_version) do update
  set evidence_grade = excluded.evidence_grade,
      evidence_score = excluded.evidence_score,
      report = excluded.report,
      generated_at = excluded.generated_at,
      updated_at = now();

  update public.client_portfolio_alerts
  set active = false, resolved_at = now(), last_seen_at = now()
  where portfolio_id = p_portfolio_id and user_id = v_user_id and active;

  insert into public.client_portfolio_alerts (
    portfolio_id, user_id, alert_key, severity, title, detail, evidence,
    active, first_seen_at, last_seen_at, resolved_at
  )
  select
    p_portfolio_id, v_user_id, item.alert_key, item.severity, item.title,
    item.detail, coalesce(item.evidence, '{}'::jsonb), true, now(), now(), null
  from jsonb_to_recordset(coalesce(p_alerts, '[]'::jsonb)) as item(
    alert_key text,
    severity text,
    title text,
    detail text,
    evidence jsonb
  )
  on conflict (portfolio_id, alert_key) do update
  set severity = excluded.severity,
      title = excluded.title,
      detail = excluded.detail,
      evidence = excluded.evidence,
      active = true,
      last_seen_at = now(),
      resolved_at = null;
end;
$$;

revoke all on function public.sync_client_portfolio_institutional_report(uuid, text, jsonb, jsonb)
  from public, anon;
grant execute on function public.sync_client_portfolio_institutional_report(uuid, text, jsonb, jsonb)
  to authenticated;
