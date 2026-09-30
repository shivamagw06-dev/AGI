-- Facts pulled out of a manager's own publication.
--
-- A 13F shows US-listed long equity at a quarter end and nothing else. A
-- manager's annual report can show what no filing does: cost basis, the
-- percentage of a company owned, and holdings that are not 13F-reportable at
-- all. Berkshire's 2025 report discloses five Japanese trading houses worth
-- $35.4bn against $15.4bn of cost, none of which appears in any 13F.
--
-- The document itself is not stored. It is the manager's own writing and its
-- own copyright, and a commercial site keeping a corpus of it is not the same
-- act as citing a figure from it. What is kept is each extracted fact and the
-- single line it came from, which is ordinary citation and is what makes the
-- fact checkable.
--
-- Nothing reaches the page unapproved. An extractor reading a table is more
-- reliable than one reading prose and neither is trustworthy enough to publish
-- unreviewed, so a fact is stored pending and a person promotes it. The
-- analyst briefs sitting in pending_review are the warning attached to that
-- design: a review queue nobody works is a feature that does not ship.

create table if not exists public.manager_publications (
  id uuid primary key default gen_random_uuid(),
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  -- What the document is, as the person pasting it describes it. Not detected:
  -- a quarterly letter carries no CIK, no fiscal-year header and no title in
  -- any fixed place, so guessing its identity would be inventing one.
  title text not null,
  -- The period the document speaks about, not when it was pasted.
  as_of_date date,
  source_url text,
  -- Whitespace-collapsed hash of the text. The same report pasted twice out of
  -- a PDF differs in line wrapping and nothing else, and re-pasting should be
  -- recognised rather than stored as a second publication.
  digest text not null unique,
  pasted_at timestamptz not null default now()
);

create table if not exists public.manager_publication_facts (
  id uuid primary key default gen_random_uuid(),
  publication_id uuid not null references public.manager_publications(id) on delete cascade,
  manager_id uuid not null references public.institutional_managers(id) on delete cascade,
  -- 'disclosed_holding' today. Kept open because a report states things that
  -- are not holdings - float, buyback policy, a stated cost of borrowing.
  kind text not null,
  issuer text,
  percent_owned numeric,
  cost_basis numeric,
  market_value numeric,
  dividends numeric,
  -- 'thousands', 'millions', 'billions', or null when the document declared
  -- none. Null means the figures are as written and nothing may scale them:
  -- "$ 6,255" is six thousand dollars or six billion depending on a header
  -- line, and this codebase has shipped a thousand-fold error once already.
  unit text check (unit is null or unit in ('thousands', 'millions', 'billions')),
  -- The line the fact came from. A reviewer approves a number against the
  -- text that produced it rather than against an assurance about the parse.
  source_excerpt text not null,
  status text not null default 'pending'
    check (status in ('pending', 'approved', 'rejected')),
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  unique (publication_id, source_excerpt)
);

create index if not exists manager_publication_facts_manager_idx
  on public.manager_publication_facts (manager_id, status);
create index if not exists manager_publication_facts_review_idx
  on public.manager_publication_facts (status, created_at)
  where status = 'pending';

alter table public.manager_publications enable row level security;
alter table public.manager_publication_facts enable row level security;
revoke all on table public.manager_publications from public, anon, authenticated;
revoke all on table public.manager_publication_facts from public, anon, authenticated;
grant select, insert, update, delete on table public.manager_publications to service_role;
grant select, insert, update, delete on table public.manager_publication_facts to service_role;

comment on table public.manager_publications is
  'Documents a manager published that were pasted in for extraction. Metadata and a digest only - the text is the manager''s own copyright and is not stored.';
comment on table public.manager_publication_facts is
  'Facts extracted from a publication, each with the line it came from. Stored pending; a person approves before anything reaches the page.';
