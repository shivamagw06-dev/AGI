-- Institutional Intelligence V3. Server-owned evidence tables remain private;
-- user workspace rows are protected by owner-scoped RLS policies.

create table if not exists public.institutional_security_classifications (
  id uuid primary key default gen_random_uuid(),
  security_key text not null,
  cusip text,
  ticker text,
  issuer_name text,
  issuer_cik text,
  sic_code text,
  sector text not null default 'Unclassified',
  industry text not null default 'Unclassified',
  valid_from date not null,
  valid_to date,
  source text not null,
  source_url text,
  source_as_of timestamptz not null default now(),
  confidence numeric(5,4) not null default 0.8 check (confidence between 0 and 1),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (security_key, valid_from, source)
);
create index if not exists institutional_classification_lookup_idx on public.institutional_security_classifications (security_key, valid_from desc);

create table if not exists public.institutional_security_prices (
  id uuid primary key default gen_random_uuid(),
  security_key text not null,
  ticker text not null,
  security_type text not null default 'equity' check (security_type in ('equity', 'benchmark')),
  price_date date not null,
  close numeric,
  adjusted_close numeric,
  currency text,
  listing_status text not null default 'unknown' check (listing_status in ('active', 'stale_or_delisted', 'unknown')),
  source text not null,
  source_as_of timestamptz not null default now(),
  created_at timestamptz not null default now(),
  unique (security_key, price_date, source)
);
create index if not exists institutional_price_lookup_idx on public.institutional_security_prices (security_key, price_date);

create table if not exists public.institutional_external_filings (
  id uuid primary key default gen_random_uuid(),
  accession_number text not null unique,
  manager_id uuid references public.institutional_managers(id) on delete set null,
  filer_cik text,
  issuer_cik text,
  ticker text,
  form_type text not null,
  event_type text not null,
  filed_at timestamptz,
  report_date date,
  source_url text not null,
  parsed_data jsonb not null default '{}'::jsonb,
  source_as_of timestamptz not null default now(),
  created_at timestamptz not null default now()
);
create index if not exists institutional_external_manager_idx on public.institutional_external_filings (manager_id, filed_at desc);
create index if not exists institutional_external_ticker_idx on public.institutional_external_filings (ticker, filed_at desc);

create table if not exists public.institutional_backtest_runs (
  id uuid primary key default gen_random_uuid(),
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  as_of_date date not null,
  strategy_key text not null,
  status text not null check (status in ('calculated', 'not_calculable')),
  methodology text not null,
  assumptions jsonb not null default '{}'::jsonb,
  metrics jsonb not null default '{}'::jsonb,
  periods jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '{}'::jsonb,
  generated_at timestamptz not null default now(),
  unique (manager_id, as_of_date, strategy_key)
);

create table if not exists public.institutional_manager_groups (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.institutional_manager_group_members (
  id uuid primary key default gen_random_uuid(),
  group_id uuid not null references public.institutional_manager_groups(id) on delete cascade,
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (group_id, manager_id)
);
create table if not exists public.institutional_watchlists (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null default auth.uid() references auth.users(id) on delete cascade,
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create table if not exists public.institutional_watchlist_items (
  id uuid primary key default gen_random_uuid(),
  watchlist_id uuid not null references public.institutional_watchlists(id) on delete cascade,
  security_key text not null,
  ticker text,
  issuer_name text,
  created_at timestamptz not null default now(),
  unique (watchlist_id, security_key)
);
create table if not exists public.institutional_personalized_alerts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  event_key text not null,
  title text not null,
  body text not null,
  severity text not null default 'info' check (severity in ('info', 'important', 'critical')),
  evidence jsonb not null default '{}'::jsonb,
  is_read boolean not null default false,
  created_at timestamptz not null default now(),
  unique (user_id, event_key)
);
create table if not exists public.institutional_intelligence_briefs (
  id uuid primary key default gen_random_uuid(),
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  filing_id uuid not null references public.institutional_filings(id) on delete cascade,
  status text not null default 'pending_review' check (status in ('pending_review', 'approved', 'rejected', 'published')),
  headline text not null,
  summary text not null,
  key_points jsonb not null default '[]'::jsonb,
  evidence jsonb not null default '{}'::jsonb,
  generated_at timestamptz not null default now(),
  reviewed_at timestamptz,
  reviewed_by text,
  reviewer_notes text,
  unique (manager_id, filing_id)
);
create index if not exists institutional_brief_status_idx on public.institutional_intelligence_briefs (status, generated_at desc);

alter table public.institutional_security_classifications enable row level security;
alter table public.institutional_security_prices enable row level security;
alter table public.institutional_external_filings enable row level security;
alter table public.institutional_backtest_runs enable row level security;
alter table public.institutional_manager_groups enable row level security;
alter table public.institutional_manager_group_members enable row level security;
alter table public.institutional_watchlists enable row level security;
alter table public.institutional_watchlist_items enable row level security;
alter table public.institutional_personalized_alerts enable row level security;
alter table public.institutional_intelligence_briefs enable row level security;

revoke all on table public.institutional_security_classifications, public.institutional_security_prices,
  public.institutional_external_filings, public.institutional_backtest_runs,
  public.institutional_intelligence_briefs from anon, authenticated;
grant all on table public.institutional_security_classifications, public.institutional_security_prices,
  public.institutional_external_filings, public.institutional_backtest_runs,
  public.institutional_intelligence_briefs to service_role;

revoke all on table public.institutional_manager_groups, public.institutional_manager_group_members,
  public.institutional_watchlists, public.institutional_watchlist_items,
  public.institutional_personalized_alerts from anon, authenticated;
grant select, insert, update, delete on table public.institutional_manager_groups,
  public.institutional_manager_group_members, public.institutional_watchlists,
  public.institutional_watchlist_items to authenticated;
grant select, update, delete on table public.institutional_personalized_alerts to authenticated;
grant all on table public.institutional_manager_groups, public.institutional_manager_group_members,
  public.institutional_watchlists, public.institutional_watchlist_items,
  public.institutional_personalized_alerts to service_role;

create policy "institutional groups select own" on public.institutional_manager_groups for select to authenticated using ((select auth.uid()) = user_id);
create policy "institutional groups insert own" on public.institutional_manager_groups for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "institutional groups update own" on public.institutional_manager_groups for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "institutional groups delete own" on public.institutional_manager_groups for delete to authenticated using ((select auth.uid()) = user_id);
create policy "institutional group members select own" on public.institutional_manager_group_members for select to authenticated using (exists (select 1 from public.institutional_manager_groups g where g.id = group_id and g.user_id = (select auth.uid())));
create policy "institutional group members insert own" on public.institutional_manager_group_members for insert to authenticated with check (exists (select 1 from public.institutional_manager_groups g where g.id = group_id and g.user_id = (select auth.uid())));
create policy "institutional group members update own" on public.institutional_manager_group_members for update to authenticated using (exists (select 1 from public.institutional_manager_groups g where g.id = group_id and g.user_id = (select auth.uid()))) with check (exists (select 1 from public.institutional_manager_groups g where g.id = group_id and g.user_id = (select auth.uid())));
create policy "institutional group members delete own" on public.institutional_manager_group_members for delete to authenticated using (exists (select 1 from public.institutional_manager_groups g where g.id = group_id and g.user_id = (select auth.uid())));
create policy "institutional watchlists select own" on public.institutional_watchlists for select to authenticated using ((select auth.uid()) = user_id);
create policy "institutional watchlists insert own" on public.institutional_watchlists for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "institutional watchlists update own" on public.institutional_watchlists for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "institutional watchlists delete own" on public.institutional_watchlists for delete to authenticated using ((select auth.uid()) = user_id);
create policy "institutional watchlist items select own" on public.institutional_watchlist_items for select to authenticated using (exists (select 1 from public.institutional_watchlists w where w.id = watchlist_id and w.user_id = (select auth.uid())));
create policy "institutional watchlist items insert own" on public.institutional_watchlist_items for insert to authenticated with check (exists (select 1 from public.institutional_watchlists w where w.id = watchlist_id and w.user_id = (select auth.uid())));
create policy "institutional watchlist items update own" on public.institutional_watchlist_items for update to authenticated using (exists (select 1 from public.institutional_watchlists w where w.id = watchlist_id and w.user_id = (select auth.uid()))) with check (exists (select 1 from public.institutional_watchlists w where w.id = watchlist_id and w.user_id = (select auth.uid())));
create policy "institutional watchlist items delete own" on public.institutional_watchlist_items for delete to authenticated using (exists (select 1 from public.institutional_watchlists w where w.id = watchlist_id and w.user_id = (select auth.uid())));
create policy "institutional alerts select own" on public.institutional_personalized_alerts for select to authenticated using ((select auth.uid()) = user_id);
create policy "institutional alerts update own" on public.institutional_personalized_alerts for update to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);
create policy "institutional alerts delete own" on public.institutional_personalized_alerts for delete to authenticated using ((select auth.uid()) = user_id);
