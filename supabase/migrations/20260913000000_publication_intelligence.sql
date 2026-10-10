-- The nine-step chain, stored against the sentence that produced each step.
--
--   WHAT happened -> WHY -> HOW the business responded -> HOW MUCH it matters
--   -> WHAT CHANGED -> WHAT MANAGEMENT EXPECTS -> RISKS -> CATALYSTS
--   -> SO WHAT for investors
--
-- Seven of those nine are sentences in the document. Two are not: a catalyst
-- and a so-what are inference across disclosures, and no sentence states
-- either. They have no rows here and never will from an extractor - the gap is
-- in the code's CHAIN definition with its reason, so a page renders the gap
-- instead of showing seven slots as if they were the chain.
--
-- `basis` is the promise attached to a row:
--   stated   - the filer wrote this sentence; source_excerpt is their words
--   derived  - arithmetic on two figures the filer states; the work is in
--              `change`, so a reviewer can check the subtraction
--   inferred - analysis; nothing reaches this table with this basis today
--
-- The document is still not stored. Each row keeps one sentence, which is
-- citation, and not the corpus, which would be republication.
--
-- Everything lands pending. A cue-matched sentence is a candidate, not a
-- finding: the cues in publicationIntelligence.js were cut down twice after
-- reading what they caught on a real 557,000-character report, and they still
-- file a cause as a response now and then.

alter table public.manager_publication_facts
  -- Null for a disclosed-holding row, which is a table fact and not a step in
  -- the chain.
  add column if not exists slot text,
  add column if not exists basis text,
  -- The metric the sentence names, from a closed list in code, or null. Null
  -- means the document named no metric we recognise - not that we guessed one.
  add column if not exists metric text,
  -- Figures as written, with the scale the document stated. Nothing here has
  -- been multiplied out: "$176 billion" is stored as 176 with scale 'billion'.
  add column if not exists figures jsonb,
  -- from, to, delta, direction and which pattern read it. Null unless the
  -- document states both endpoints or states the delta itself.
  add column if not exists change jsonb,
  add column if not exists paragraph integer;

alter table public.manager_publication_facts
  drop constraint if exists manager_publication_facts_slot_check;
alter table public.manager_publication_facts
  add constraint manager_publication_facts_slot_check check (
    slot is null or slot in (
      'what_happened', 'why', 'how', 'how_much', 'what_changed',
      'expectations', 'risks', 'catalysts', 'so_what'
    )
  );

alter table public.manager_publication_facts
  drop constraint if exists manager_publication_facts_basis_check;
alter table public.manager_publication_facts
  add constraint manager_publication_facts_basis_check check (
    basis is null or basis in ('stated', 'derived', 'inferred')
  );

-- One sentence can legitimately fill several slots: "Underwriting expenses
-- increased 34.2% in 2025 compared to 2024" is both an amount and a change,
-- and the sentence after it is both a why and a how. The original uniqueness
-- was on (publication_id, source_excerpt), which let the first slot in and
-- silently dropped the rest.
--
-- Widening it drops a constraint and adds a broader one. No row is deleted and
-- nothing that was permitted becomes forbidden; every pair the old constraint
-- accepted is still accepted.
--
-- `nulls not distinct` is load-bearing. A disclosed-holding row has no slot,
-- and under the default rule two holdings with the same excerpt would both be
-- inserted because null never equals null - the uniqueness that already
-- protects those rows would quietly stop applying to them. It needs
-- PostgreSQL 15 or later; on an older server this statement fails outright,
-- which is the right failure.
alter table public.manager_publication_facts
  drop constraint if exists manager_publication_facts_publication_id_source_excerpt_key;
create unique index if not exists manager_publication_facts_claim_key
  on public.manager_publication_facts
  (publication_id, slot, source_excerpt) nulls not distinct;

create index if not exists manager_publication_facts_slot_idx
  on public.manager_publication_facts (manager_id, slot, status);

comment on column public.manager_publication_facts.slot is
  'Which step of the chain this claim answers. Null for a disclosed-holding row.';
comment on column public.manager_publication_facts.basis is
  'stated = the filer''s own sentence; derived = arithmetic on two stated figures, shown in change; inferred = analysis.';
comment on column public.manager_publication_facts.change is
  'from/to/delta/direction and the pattern that read it. Null unless the document states both endpoints or the delta itself - a stated delta with one endpoint is never solved for the other.';
