-- A disclosed figure, keyed by what it is rather than what it measures.
--
-- Reliance's annual report states capital expenditure three times: ₹1,44,271
-- crore in the management discussion, the same figure in the segment note, and
-- ₹1,22,916 crore in the cash flow statement for property, plant, equipment,
-- spectrum and intangibles. Free cash flow computed from the first is ₹47,842
-- crore and from the last ₹69,197 crore - 44.6% apart, from one ₹21,355 crore
-- difference that is itself 17.4% of the cash figure.
--
-- company_financials holds one column per line item and therefore one of those
-- three. This table holds all of them, because they are not a disagreement -
-- they are observations of one concept under different definitions, and
-- deciding whether they conflict is a later step that needs them all.
create table if not exists public.company_facts (
  id uuid primary key default gen_random_uuid(),

  -- ── what the fact is ──────────────────────────────────────────────
  company text not null,
  period_end date not null,
  period_type text not null default 'annual' check (period_type in ('annual', 'quarter', 'half')),
  -- The economic thing being measured: capex, revenue, ebitda, debt, cfo.
  concept text not null,
  -- How it was measured, normalised. Free text accumulates seventeen spellings
  -- of one definition; an id does not. See factOntology.js for the register.
  definition_id text not null,
  -- Consolidated or standalone, and separately whose figures these are: the
  -- group, a subsidiary, a segment, a joint venture. Standalone against
  -- consolidated alone is not enough to keep a segment apart from a group.
  accounting_scope text not null default 'consolidated'
    check (accounting_scope in ('consolidated', 'standalone')),
  entity_scope text not null default 'group'
    check (entity_scope in ('group', 'company', 'subsidiary', 'segment', 'jv', 'associate')),
  measurement_basis text not null
    check (measurement_basis in ('cash', 'accrual', 'segment_reporting', 'management_adjusted', 'statutory')),
  segment text,
  geography text,
  -- Anything else that distinguishes two observations: a maturity bucket, a
  -- debt type, a subscriber type. Held here so a new qualifier needs no
  -- migration.
  dimensions jsonb not null default '{}'::jsonb,
  currency text not null,
  -- What one unit of `value` means: 1, 100000 (lakh), 10000000 (crore).
  unit numeric not null check (unit > 0),

  -- ── restatement lineage ───────────────────────────────────────────
  -- FY25 as first reported and FY25 restated in the FY26 report are two facts.
  -- Letting one overwrite the other loses the restatement, which is usually
  -- the thing worth knowing.
  reported_in_document text not null,
  original_or_restated text not null default 'original'
    check (original_or_restated in ('original', 'restated')),
  supersedes_fact_id uuid references public.company_facts(id) on delete set null,

  -- ── the value and where it came from ──────────────────────────────
  value numeric,
  -- stated: the document says it. derived: arithmetic over stated inputs.
  -- inferred: supported by facts, entailed by none of them. unsupported:
  -- nothing supports it, and it is not published.
  verdict text not null default 'stated'
    check (verdict in ('stated', 'derived', 'inferred', 'unsupported')),
  -- For a derived fact, the facts it was computed from - by id, so a restated
  -- input can invalidate everything downstream instead of leaving a stale
  -- figure that still looks computed.
  input_fact_ids jsonb,
  formula text,
  -- The issuer's own words, never discarded: "Value of Sales and Services" is
  -- how Reliance says revenue.
  as_reported_label text,
  source_document_id text,
  source_section text,
  source_page integer,
  source_sentence text,
  confidence numeric check (confidence is null or (confidence >= 0 and confidence <= 1)),

  imported_at timestamptz not null default now()
);

-- One observation per definition per period per scope per document. The
-- document is in the key so a restatement is an insert, not an overwrite.
create unique index if not exists company_facts_identity_idx
  on public.company_facts (company, period_end, period_type, accounting_scope, entity_scope,
    concept, definition_id, coalesce(segment, ''), coalesce(geography, ''),
    dimensions, reported_in_document);

create index if not exists company_facts_lookup_idx
  on public.company_facts (company, concept, period_end desc);

alter table public.company_facts enable row level security;
revoke all on table public.company_facts from public, anon, authenticated;
grant select, insert, update, delete on table public.company_facts to service_role;

comment on table public.company_facts is
  'Disclosed figures keyed by concept and definition, not by line item. Two disclosures using different definitions are two facts. Restatements are kept alongside the original rather than overwriting it.';
