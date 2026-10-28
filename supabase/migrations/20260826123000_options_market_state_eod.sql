-- One row per underlying per trading day: the conditions a signal was seen in.
--
-- Strictly what was knowable at that close. Realised volatility looks
-- backwards, positioning is the book as it stood, and the implied levels come
-- from that day's fitted surfaces. Nothing here may be computed from a later
-- date -- not because it would be inaccurate, but because it would be
-- accurate, and a study conditioned on it would find an edge that could never
-- have been traded.
--
-- The variance premium against FORWARD realised volatility is deliberately
-- absent for the same reason. That is an outcome, and it belongs in the
-- outcome table beside the returns it is measured with.

CREATE TABLE IF NOT EXISTS public.options_market_state_eod (
  observation_date        date        NOT NULL,
  underlying_symbol       text        NOT NULL,

  spot                    numeric(14,4),
  return_1d_pct           numeric(10,4),

  -- Trailing, annualised, from closes up to and including today.
  realised_vol_5d         numeric(10,4),
  realised_vol_20d        numeric(10,4),

  -- Level and shape, read from the day's fitted surfaces.
  atm_iv_front            numeric(10,4),
  atm_iv_30d              numeric(10,4),
  term_slope              numeric(10,4),   -- 30d minus front, vol points
  risk_reversal_30d       numeric(10,4),
  butterfly_30d           numeric(10,4),
  -- Share of the day's expiries whose risk reversal has the same sign as the
  -- thirty-day value. A day where the expiries disagree is a day whose skew is
  -- not well determined, which a study should be able to see rather than have
  -- decided for it.
  skew_agreement          numeric(6,4),

  -- Implied against trailing realised. Not the variance risk premium: that
  -- needs the volatility that followed, which this row must not know.
  iv_minus_trailing_rv    numeric(10,4),

  -- Positioning, near-dated expiries only. A December strike carries open
  -- interest that says nothing about this week.
  oi_pcr                  numeric(10,4),
  volume_pcr              numeric(10,4),
  change_oi_pcr           numeric(10,4),
  total_call_oi           bigint,
  total_put_oi            bigint,

  max_pain                numeric(14,4),
  spot_to_max_pain_pct    numeric(10,4),
  peak_call_oi_strike     numeric(14,4),
  peak_put_oi_strike      numeric(14,4),
  call_oi_concentration   numeric(10,4),   -- share of call OI at its peak strike
  put_oi_concentration    numeric(10,4),

  expiries_used           smallint    NOT NULL,
  contracts_used          smallint    NOT NULL,
  state_quality           text        NOT NULL,

  source                  text        NOT NULL DEFAULT 'nse_bhavcopy',
  pipeline_version        text        NOT NULL,
  state_version           text        NOT NULL,
  built_at                timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT options_market_state_quality_chk
    CHECK (state_quality IN ('high', 'medium', 'low')),
  CONSTRAINT options_market_state_pkey
    PRIMARY KEY (observation_date, underlying_symbol)
);

CREATE INDEX IF NOT EXISTS options_market_state_underlying_date_idx
  ON public.options_market_state_eod (underlying_symbol, observation_date);

ALTER TABLE public.options_market_state_eod ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.options_market_state_eod FROM anon, authenticated;

COMMENT ON TABLE public.options_market_state_eod IS
  'Daily options market conditions per underlying. Contains only what was '
  'knowable at that close: no column may be computed from a later date.';
COMMENT ON COLUMN public.options_market_state_eod.iv_minus_trailing_rv IS
  'Implied minus TRAILING realised volatility. Not the variance risk premium '
  '-- that compares implied to the volatility that followed, which is an '
  'outcome and lives with the returns.';
COMMENT ON COLUMN public.options_market_state_eod.max_pain IS
  'Strike minimising total intrinsic value owed by writers across near-dated '
  'expiries, from open interest. A positioning observation, not a forecast.';
