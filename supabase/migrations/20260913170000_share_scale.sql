-- A share count is not money, and is rarely reported in the same unit.
--
-- company_financials carried one scale for the whole row. Berkshire's 2025
-- statements report money in millions and 1,438,223 Class A shares in shares,
-- so loading the share count under the row's scale would have claimed 1.4
-- trillion shares. It was left out instead, which left questions 76 and 77 -
-- whether shares were issued, and whether the count rose or fell -
-- unanswerable for the one company that had been loaded.
--
-- Kept separate rather than normalised to absolute, for the same reason the
-- money scale is: a figure should read back as it was reported.
alter table public.company_financials
  add column if not exists share_scale numeric check (share_scale > 0);

comment on column public.company_financials.share_scale is
  'What one unit of share_count means: 1 for actual shares, 1000000 where a filing reports shares in millions. Required whenever share_count is present, never assumed.';
