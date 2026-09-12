-- filed_at on its own.
--
-- institutional_external_filings carries (manager_id, filed_at desc) and
-- (ticker, filed_at desc). Neither answers a question about filed_at alone -
-- Postgres will not skip the leading column - so the research layer's
-- `order by filed_at desc limit 100` was a sequential scan and a sort of the
-- whole table. Measured at 4.08 seconds for a hundred rows, which was a third
-- of that page's load once sector rotation stopped being the rest of it.
--
-- Written with `if not exists` because the useful way to create it on a live
-- table is `create index concurrently`, which cannot run inside a transaction
-- and therefore cannot run inside a migration. Run that by hand first and this
-- becomes a no-op that records the index in schema history; run only this and
-- it builds with a brief lock on writes instead.
create index if not exists institutional_external_filings_filed_at_idx
  on public.institutional_external_filings (filed_at desc);
