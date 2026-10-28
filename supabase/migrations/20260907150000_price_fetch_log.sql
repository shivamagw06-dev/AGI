-- When each symbol was last fetched.
--
-- The backfill worked this out from the price rows themselves, which does not
-- scale and got worse the more it succeeded: every row it writes carries the
-- run's timestamp, so after a full pass the "recently fetched" filter matches
-- several million rows and the client pages through all of them to derive one
-- date per symbol. An index makes each page quick and leaves the number of
-- pages unchanged.
--
-- One row per symbol answers the question directly. It also records outcomes
-- that write no prices at all - a symbol Yahoo does not know, or whose history
-- is a single-bar stub - which the price rows could never represent, so those
-- were refetched on every run forever.
create table if not exists public.institutional_price_fetch_log (
  ticker text primary key,
  fetched_at timestamptz not null default now(),
  status text not null,
  bars integer not null default 0,
  detail text
);

alter table public.institutional_price_fetch_log enable row level security;

-- Service role only, like the rest of the identifier and price tables. No
-- anon or authenticated grant: nothing user-facing reads this.
revoke all on public.institutional_price_fetch_log from anon, authenticated;
