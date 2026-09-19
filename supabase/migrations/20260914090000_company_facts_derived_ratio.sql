-- A ratio is not measured the way its inputs are.
--
-- The calculator produces figures the filing does not state: Reliance's Retail
-- EBITDA margin of 8.237% from 27,034 over 3,28,202, net debt to EBITDA of
-- 0.60x, free cash flow margins on each of two capital expenditure
-- definitions. Calling any of those "accrual" or "cash" would claim something
-- about a quotient that is not true of it, and would let it be compared with
-- figures it cannot be compared with.
--
-- The check constraint on company_facts predates that basis, so every derived
-- ratio the calculator produces is currently rejected at insert. Widening a
-- check constraint cannot fail on rows already stored.
alter table public.company_facts
  drop constraint if exists company_facts_measurement_basis_check;

alter table public.company_facts
  add constraint company_facts_measurement_basis_check
  check (measurement_basis in (
    'cash', 'accrual', 'segment_reporting', 'management_adjusted', 'statutory',
    'derived_ratio'
  ));

comment on column public.company_facts.measurement_basis is
  'How the figure was measured, which is not what it measures. derived_ratio is for quotients, whose basis is neither of their inputs''.';
