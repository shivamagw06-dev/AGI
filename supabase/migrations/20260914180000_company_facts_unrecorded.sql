-- A basis the source never recorded.
--
-- company_financials held one column per line item. Ten of its twenty-six
-- columns name more than one definition in the register, and for capital
-- expenditure, EBIT and dividends those definitions are measured differently -
-- cash against accrual against the segment note. For those three the basis is
-- genuinely unknown, not merely unstated, and the figures still have to be
-- storable: dropping them loses data the questions want most, and storing them
-- under a basis nobody recorded would make the uncertainty invisible.
--
-- No purpose in the reconciliation layer admits 'unrecorded', so a figure
-- stored this way is visible and queryable and cannot be selected for work
-- that depends on knowing how it was measured. It carries a currency like any
-- other amount of money.
alter table public.company_facts
  drop constraint if exists company_facts_measurement_basis_check;

alter table public.company_facts
  add constraint company_facts_measurement_basis_check
  check (measurement_basis in (
    'cash', 'accrual', 'segment_reporting', 'management_adjusted', 'statutory',
    'derived_ratio', 'count', 'unrecorded'
  ));

comment on column public.company_facts.measurement_basis is
  'How the figure was measured, which is not what it measures. derived_ratio and count are dimensionless and carry no currency. unrecorded means the source supplied a figure without saying how it was measured; no purpose selects one.';
