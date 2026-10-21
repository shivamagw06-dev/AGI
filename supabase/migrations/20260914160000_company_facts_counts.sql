-- A share count is not an amount of money and not a quotient.
--
-- Answering "has the share count increased or decreased" needs shares
-- outstanding as a fact, and a share count has no currency - storing 'INR'
-- against 1,353 crore shares would let them be summed with rupees. The same is
-- already true of ratios, so the rule is one rule: a figure is either an
-- amount of money, which must say which money, or it is dimensionless.
alter table public.company_facts
  drop constraint if exists company_facts_measurement_basis_check;

alter table public.company_facts
  add constraint company_facts_measurement_basis_check
  check (measurement_basis in (
    'cash', 'accrual', 'segment_reporting', 'management_adjusted', 'statutory',
    'derived_ratio', 'count'
  ));

alter table public.company_facts
  drop constraint if exists company_facts_currency_required;

alter table public.company_facts
  add constraint company_facts_currency_required
  check ((measurement_basis in ('derived_ratio', 'count')) = (currency is null));

comment on column public.company_facts.currency is
  'The money the figure is stated in. NULL exactly when the basis is derived_ratio or count, which are dimensionless; every other basis requires it.';
