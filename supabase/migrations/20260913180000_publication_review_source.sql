-- Who approved a fact: a person, or a rule.
--
-- Two kinds of claim can be published without anyone reading them. A change
-- where the document states both endpoints is the filer's sentence plus a
-- subtraction anyone can check against it. An amount whose metric is on the
-- closed list is quotation with a label the filer wrote. Everything a cue
-- matched stays pending, because `why`, `risks`, `how` and `expectations` are
-- a regular expression's guess at what a sentence is doing - the expectations
-- slot runs at roughly half precision, with "we expect the resolution periods
-- will be very long" sitting beside "we expect to write less reinsurance
-- premium".
--
-- Without this column an approved row cannot say which happened, and a page
-- would present a rule's approval as a person's. That is the distinction
-- worth keeping: a rule certifies that the row quotes the document
-- accurately. It does not certify the fact is worth reading - "our insurance
-- businesses' ability to declare ordinary dividends ... permitting up to $31
-- billion" is an accurate amount with a named metric and is also dull.
-- Accuracy is a property of the extraction and can be decided by rule;
-- interest is editorial and cannot.

alter table public.manager_publication_facts
  add column if not exists reviewed_by text;

alter table public.manager_publication_facts
  drop constraint if exists manager_publication_facts_reviewed_by_check;
alter table public.manager_publication_facts
  add constraint manager_publication_facts_reviewed_by_check check (
    reviewed_by is null or reviewed_by in ('rule', 'person')
  );

-- A reviewed row records who reviewed it. A pending row has reviewed neither
-- way, so both fields stay null together.
alter table public.manager_publication_facts
  drop constraint if exists manager_publication_facts_review_pair_check;
alter table public.manager_publication_facts
  add constraint manager_publication_facts_review_pair_check check (
    (status = 'pending' and reviewed_by is null)
    or (status in ('approved', 'rejected') and reviewed_by is not null)
  );

-- The queue a person actually works: pending claims only, worst-attributed
-- first is a caller's choice, but the index is what makes it cheap.
create index if not exists manager_publication_facts_queue_idx
  on public.manager_publication_facts (manager_id, slot, created_at)
  where status = 'pending';

comment on column public.manager_publication_facts.reviewed_by is
  'rule = approved automatically because the claim is quotation plus arithmetic; person = a human approved or rejected it. Null while pending. A page must not present the first as the second.';
