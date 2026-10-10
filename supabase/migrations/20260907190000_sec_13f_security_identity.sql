-- The SEC's own list of 13(f) securities, as the identity spine.
--
-- Identifier resolution had one source: a vendor that answers "what does this
-- CUSIP map to now". That question cannot be asked about 2019, and it cannot
-- be asked about a security whose CUSIP has since changed - both return "No
-- identifier found", which is also what a genuinely unlisted security returns.
-- The three were indistinguishable, so the backfill stalled at 54.66% against
-- a fixed cohort and every retry re-asked the same unanswerable question.
--
-- Measured against the official list, the forty largest unresolved holdings
-- were 17 common equities, 12 CUSIP changes, 8 convertible notes and 3
-- preferreds. About seventy per cent was identity; thirty per cent was
-- instruments that are not common equity and never will be.
--
-- The SEC publishes this list every quarter, which is what makes it usable
-- here: point-in-time by construction rather than by assumption. Thirty
-- quarters, 2019Q1 to 2026Q2, give 42,683 distinct CUSIPs and 1,660 identifier
-- changes - Aon's 2020 Ireland redomicile, Atlassian's 2022 US domestication,
-- Unilever, Cooper, Qiagen, Cushman & Wakefield.
--
-- Licensing. The list carries a CUSIP Global Services and American Bankers
-- Association copyright with a "no redistribution without permission" notice.
-- Preparing and processing 13F data is its stated purpose, so holding it here
-- to resolve identity is within that. These tables are service-role only: no
-- anon or authenticated grant is issued, and nothing reads them through the
-- public API. Tickers and issuer names derived downstream are not CGS data.

create table if not exists public.sec_13f_securities (
  cusip text primary key,

  -- The window the identifier was actually on the list. Both ends matter: the
  -- last quarter is how a superseded identifier is recognised as superseded
  -- rather than as missing.
  first_quarter text not null,
  last_quarter text not null,

  issuer_name text not null,

  -- The SEC's own description, kept verbatim. It is the field that separates a
  -- company's stock from its convertible notes, its preferred and its options,
  -- all of which carry the same issuer name in a 13F filing.
  description text not null,

  security_class text not null
    check (security_class in ('equity', 'debt', 'preferred', 'option', 'derivative', 'other', 'unknown')),

  -- Marked on the list for issues that also have listed options.
  has_listed_options boolean not null default false,

  observed_quarters integer not null default 0,
  updated_at timestamptz not null default now(),

  constraint sec_13f_securities_quarter_order check (first_quarter <= last_quarter)
);

create index if not exists sec_13f_securities_class_idx
  on public.sec_13f_securities (security_class);
create index if not exists sec_13f_securities_name_idx
  on public.sec_13f_securities (issuer_name);

-- Which identifiers are the same security.
--
-- A rename shows as the old identifier ending in exactly the quarter the new
-- one begins. Ending later means the two ran alongside and are different
-- securities - AstraZeneca's ordinary shares beside its ADR, Amcor's ORD line
-- beside its COM NEW line - and ending earlier leaves a gap, which Seadrill
-- and Aspen both show across five and six years respectively. Neither is a
-- rename, and both were chained by earlier versions of this rule.
--
-- There is a further case. When the changeover falls in the last quarter
-- loaded, the evidence that would settle it - does the old identifier appear
-- again? - has not been published yet. Ascendis shows 04351P101 across seven
-- years and K08588103 in the final quarter alone, which is the shape of both a
-- rename in progress and a newly listed second class. 239 of 1,660 chains end
-- on such a link; they are recorded as separate securities and flagged, and
-- the next quarterly load will join them if the old identifier does not return.
--
-- A link that does not hold ends a chain rather than voiding the group, so a
-- security with four verified reverse splits and an unproven fifth keeps the
-- four. An unresolved security is a gap; a wrongly merged one puts one
-- company's holdings under another company's ticker.
create table if not exists public.sec_13f_identity_chain (
  cusip text primary key references public.sec_13f_securities(cusip) on delete cascade,

  -- The earliest identifier in the chain, so history filed under the old CUSIP
  -- is not orphaned when the identifier changes.
  security_key text not null,

  -- Normalised issuer name the chain was grouped on. Retained so a disputed
  -- link can be traced back to what it was grouped by.
  name_key text not null,

  -- The chain was cut because its changeover sits on the edge of the loaded
  -- window, not because the evidence says these are different securities.
  held_at_edge boolean not null default false,
  chain_length integer not null default 1,
  updated_at timestamptz not null default now()
);

create index if not exists sec_13f_identity_chain_key_idx
  on public.sec_13f_identity_chain (security_key);

-- What each load did, so a bad parse is visible rather than inferred.
--
-- Three quarters once downloaded and parsed to almost nothing without erroring
-- - 2025Q2 and 2025Q3 to zero rows, 2025Q4 to 2,498 equities against about
-- 7,000 in its neighbours - because the PDF column layout had shifted. The run
-- reported success. Worse, a security absent from a quarter that never parsed
-- is indistinguishable from one that was delisted, so the holes manufactured
-- 120 false identifier changes. Recording per-quarter counts makes that shape
-- of failure visible in the data rather than only in a log nobody reads.
create table if not exists public.sec_13f_list_loads (
  id uuid primary key default gen_random_uuid(),
  quarter text not null,
  loaded_at timestamptz not null default now(),
  source_url text,
  rows_parsed integer not null default 0,
  equities_parsed integer not null default 0,
  notes text
);

create index if not exists sec_13f_list_loads_quarter_idx
  on public.sec_13f_list_loads (quarter, loaded_at desc);

alter table public.sec_13f_securities enable row level security;
alter table public.sec_13f_identity_chain enable row level security;
alter table public.sec_13f_list_loads enable row level security;

-- Licensed reference data and operational records. Only the loader writes and
-- only server-side resolution reads, so no anon or authenticated grant exists.
revoke all on table public.sec_13f_securities from anon, authenticated;
revoke all on table public.sec_13f_identity_chain from anon, authenticated;
revoke all on table public.sec_13f_list_loads from anon, authenticated;
grant all on table public.sec_13f_securities to service_role;
grant all on table public.sec_13f_identity_chain to service_role;
grant all on table public.sec_13f_list_loads to service_role;
