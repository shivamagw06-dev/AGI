-- Canonical end-of-day option observations, derived from the NSE F&O bhavcopy.
--
-- One row is one contract on one trading day: what it traded at, what was open
-- against it, and the volatility implied from the forward. Roughly 8.8M rows a
-- year across every underlying with listed options.
--
-- Three things this table deliberately does NOT hold:
--
--   * Greeks. Delta, gamma, theta and vega are functions of columns that are
--     here, so persisting them costs storage on every row to save arithmetic
--     the research layer can redo. They are derived there instead, unless a
--     query pattern later proves they must be materialised.
--   * Surfaces and market state. ATM IV, skew, PCR and max pain describe an
--     underlying and expiry, not a contract. Denormalising them onto every row
--     would repeat one value across a thousand strikes.
--   * The raw file. Bhavcopy stays immutable in object storage. This is the
--     normalised read of it, and can be rebuilt from it.
--
-- Versioning matters more than it looks. The forward inference, the rate
-- assumption, the solver and the quality gates will all improve. Rows carry the
-- version that produced them so a later comparison cannot silently mix two
-- methodologies -- which is the failure that looks like a discovery.

CREATE TABLE IF NOT EXISTS public.option_eod_observation (
  observation_date      date        NOT NULL,
  underlying_symbol     text        NOT NULL,
  expiry                date        NOT NULL,
  strike                numeric(14,4) NOT NULL,
  option_type           text        NOT NULL,
  dte_days              smallint    NOT NULL,

  open_price            numeric(14,4),
  high_price            numeric(14,4),
  low_price             numeric(14,4),
  close_price           numeric(14,4),
  settlement_price      numeric(14,4),

  volume                bigint,
  open_interest         bigint,
  change_open_interest  bigint,

  underlying_spot       numeric(14,4),
  forward               numeric(14,4) NOT NULL,
  forward_source        text        NOT NULL,
  forward_quality       text        NOT NULL,
  forward_pair_count    smallint,
  forward_dispersion_bp numeric(10,2),

  moneyness             numeric(12,6),
  log_moneyness         numeric(12,6),

  -- Null with a reason, never a clamped number. A volatility pinned to a
  -- solver bound looks like data and drags every percentile it lands in.
  implied_volatility    numeric(10,4),
  iv_quality            text        NOT NULL,

  isin                  text,
  source                text        NOT NULL DEFAULT 'nse_bhavcopy',
  pipeline_version      text        NOT NULL,
  pricing_version       text        NOT NULL,
  ingested_at           timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT option_eod_observation_type_chk
    CHECK (option_type IN ('CE', 'PE')),
  CONSTRAINT option_eod_observation_forward_source_chk
    CHECK (forward_source IN ('future', 'parity', 'spot')),
  CONSTRAINT option_eod_observation_forward_quality_chk
    CHECK (forward_quality IN ('high', 'medium', 'low')),
  -- A contract is unique per day; re-ingesting a day must update, not multiply.
  -- The partition key has to lead the key on a partitioned table.
  CONSTRAINT option_eod_observation_pkey
    PRIMARY KEY (observation_date, underlying_symbol, expiry, strike, option_type)
) PARTITION BY RANGE (observation_date);

-- Only what research actually filters on. Every extra index is paid on each of
-- ~35,000 inserts a day, and this table is written far more than it is queried.
CREATE INDEX IF NOT EXISTS option_eod_observation_underlying_date_idx
  ON public.option_eod_observation (underlying_symbol, observation_date);
CREATE INDEX IF NOT EXISTS option_eod_observation_underlying_expiry_date_idx
  ON public.option_eod_observation (underlying_symbol, expiry, observation_date);
CREATE INDEX IF NOT EXISTS option_eod_observation_date_expiry_idx
  ON public.option_eod_observation (observation_date, expiry);


-- Monthly partitions. Called by the ingest before it writes, so a new month
-- does not need a human to remember.
CREATE OR REPLACE FUNCTION public.ensure_option_eod_partition(target date)
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
  start_at date := date_trunc('month', target)::date;
  end_at   date := (date_trunc('month', target) + interval '1 month')::date;
  part     text := format('option_eod_observation_%s', to_char(start_at, 'YYYYMM'));
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_class WHERE relname = part
  ) THEN
    EXECUTE format(
      'CREATE TABLE public.%I PARTITION OF public.option_eod_observation '
      'FOR VALUES FROM (%L) TO (%L)', part, start_at, end_at);
  END IF;
  RETURN part;
END;
$$;


-- Research data, not user data. No policy is defined on purpose: with RLS on
-- and no policy, anon and authenticated read nothing, while the service role
-- the ingest uses bypasses RLS. Adding a public read policy here would put the
-- whole option history behind the browser's anon key.
ALTER TABLE public.option_eod_observation ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON public.option_eod_observation FROM anon, authenticated;

COMMENT ON TABLE public.option_eod_observation IS
  'Canonical EOD option observations from the NSE F&O bhavcopy. End-of-day '
  'only: no intraday path, so studies built on it are close-to-close and must '
  'not be merged with the live 5-30 minute repricing evidence.';
COMMENT ON COLUMN public.option_eod_observation.forward IS
  'Forward used to imply volatility. Traded future where one exists, else a '
  'median put-call-parity forward across near-money pairs, else spot.';
COMMENT ON COLUMN public.option_eod_observation.iv_quality IS
  'ok | weak_forward | below_intrinsic | unsolved | implausible | expiring | '
  'no_forward. A failed solve stays null rather than being clamped.';
