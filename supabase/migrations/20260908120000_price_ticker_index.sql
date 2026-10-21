-- Prices are looked up by ticker and date, and nothing indexed that.
--
-- The table carries (security_key, price_date) and (source_as_of, ticker).
-- Revaluing a disclosed book asks for a date window against a list of tickers,
-- which matches neither: security_key leads the first, and source_as_of leads
-- the second. Every such query was a sequential scan of three million rows.
create index if not exists institutional_price_ticker_date_idx
  on public.institutional_security_prices (ticker, price_date)
  include (close);
