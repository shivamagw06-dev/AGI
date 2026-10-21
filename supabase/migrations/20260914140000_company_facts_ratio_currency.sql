-- A ratio has no currency, and saying it has one is a lie about the number.
--
-- company_facts.currency is NOT NULL, which is right for every figure that is
-- an amount of money and wrong for the ones that are not. Reliance's Retail
-- EBITDA margin of 8.237% is not 8.237% of rupees; net debt to EBITDA of 0.60x
-- is not 0.60 crore. Storing 'INR' against either would put a unit on a
-- quotient that has none, and would let it be summed or converted.
--
-- Every derived ratio the calculator produces currently fails to insert. The
-- fix is not to make currency optional - for an amount of money it is still
-- mandatory, and a missing one is a bug rather than a ratio. It is to make the
-- requirement conditional on what kind of figure this is.
alter table public.company_facts
  alter column currency drop not null;

alter table public.company_facts
  add constraint company_facts_currency_required
  check (measurement_basis = 'derived_ratio' or currency is not null);

comment on column public.company_facts.currency is
  'The money the figure is stated in. NULL only for a derived_ratio, which is a quotient and has none; every other basis requires it.';
