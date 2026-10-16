-- Which business a claim is about, and which market question it answers.
--
-- "We expect to write less reinsurance premium" is only worth storing if
-- someone asking what Berkshire expects from the insurance market can find it.
-- That needs two things the sentence does not always carry: the segment it
-- belongs to and the theme it speaks to.
--
-- Both come from closed lists in publicationSegments.js. A segment is a
-- business the filer reports; a theme is a market condition the filer writes
-- about. Neither is inferred from surrounding words - a label nobody wrote is
-- indistinguishable from one the filer did, once it is sitting in a column.
--
-- `segment_source` is why this is reviewable. An annual report's MD&A is
-- organised under segment headings, and the sentences beneath one are about
-- that segment without repeating its name, so a heading is inherited. That is
-- weaker evidence than the sentence naming its own business, and the column
-- says which happened:
--
--   in_sentence  - the sentence named the business
--   from_heading - inherited from the section it sits under, within 25
--                  sentences of the heading
--
-- Unbounded inheritance gave 661 of 665 claims a segment on a 557,000-
-- character report: "Pilot" collected 88 because the heading was set once in
-- the shareholder letter and never cleared, and the notes and risk factors,
-- which carry no segment headings at all, inherited whatever preceded them.
-- A third of claims now carry no segment, which is the honest answer for a
-- sentence in the notes.

alter table public.manager_publication_facts
  -- Null when the sentence named no business and sat under no section heading.
  -- Not guessed from context.
  add column if not exists segment text,
  add column if not exists segment_source text,
  -- Several is normal: "additional capital entered the market, resulting in
  -- lower pricing" answers a question about competition and about pricing.
  add column if not exists themes text[];

alter table public.manager_publication_facts
  drop constraint if exists manager_publication_facts_segment_source_check;
alter table public.manager_publication_facts
  add constraint manager_publication_facts_segment_source_check check (
    (segment is null and segment_source is null)
    or (segment is not null and segment_source in ('in_sentence', 'from_heading'))
  );

-- Answering "what does management expect from the insurance market" is a scan
-- of one manager's claims filtered by slot and segment.
create index if not exists manager_publication_facts_segment_idx
  on public.manager_publication_facts (manager_id, segment, slot, status);
-- Themes are asked about across segments: AI power demand shows up under BHE
-- and under a manufacturing subsidiary doing data-center construction.
create index if not exists manager_publication_facts_themes_idx
  on public.manager_publication_facts using gin (themes);

comment on column public.manager_publication_facts.segment is
  'The reported business this claim is about, from a closed list in code. Null when the sentence named none and no section heading applied.';
comment on column public.manager_publication_facts.segment_source is
  'in_sentence = the sentence named the business; from_heading = inherited from the section it sits under. A heading is weaker evidence and the column says so.';
comment on column public.manager_publication_facts.themes is
  'Market conditions the sentence carries, from a closed list. Never inherited from a heading - a section about BHE covers both power demand and tax policy.';
