-- Freshness lookups on the price table need an index.
--
-- The backfill asks which symbols it has already fetched, which is a filter
-- on source_as_of. There was no index on that column, so the question became
-- a sequential scan of every price row and hit the two-minute statement
-- timeout - the same shape as the trigger scan that cost 123 seconds before
-- the identifier work started.
--
-- Ticker is carried in the index so the scan answers the whole query without
-- returning to the heap: the backfill reads exactly these two columns.
create index if not exists institutional_price_fetched_idx
  on public.institutional_security_prices (source_as_of, ticker);
