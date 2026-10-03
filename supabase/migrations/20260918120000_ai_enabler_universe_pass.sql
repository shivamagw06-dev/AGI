-- Stage 1 of the India AI enablers screen, over the whole exchange.
--
-- One row per listed company per run, whatever happened to it. The table
-- exists so that "not examined" and "examined and not nominated" are
-- different rows rather than the same absence. Nomination decides what gets
-- read for evidence; it never admits a company.
--
-- Create-only. Nothing existing is altered or dropped.
create table if not exists public.ai_enabler_universe_pass (
  run_id            text        not null,
  symbol            text        not null,
  isin              text,
  name              text,
  series            text,
  disposition       text        not null
    check (disposition in ('NOMINATED', 'NOT_NOMINATED', 'NO_PROFILE', 'PROFILE_ERROR', 'NO_ISIN')),
  sector            text,
  nomination        jsonb,
  description_chars integer,
  error             text,
  fetched_at        timestamptz not null,
  primary key (run_id, symbol)
);

comment on table public.ai_enabler_universe_pass is
  'Stage 1 of the AI enablers screen: every NSE equity, one outcome each. nomination holds the sub-layers and matched terms from the company''s own business description. Nomination selects what to read; it does not admit.';

create index if not exists ai_enabler_universe_pass_disposition
  on public.ai_enabler_universe_pass (run_id, disposition);

-- Written and read only by the server with the service role; no public access.
alter table public.ai_enabler_universe_pass enable row level security;
