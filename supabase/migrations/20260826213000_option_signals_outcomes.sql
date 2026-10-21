-- Signals, and what happened after them. Two tables, on purpose.
--
-- A signal is a claim made on a date from what was knowable then. An outcome is
-- what the market did next. Keeping them apart is what makes the pair usable:
-- signals can be recomputed when a definition improves without touching the
-- record of what followed, and an outcome can never leak backwards into the
-- condition that selected it.
--
-- The join is signal_id, so a study is a query rather than a rebuild:
--
--   where signal_family = 'SKEW' and signal_zscore < -2
--     and dte_days between 7 and 21 and forward_quality = 'high'
--
-- and the forward return distribution comes back for exactly those rows.

CREATE TABLE IF NOT EXISTS public.option_signal_observation (
  signal_id          text        PRIMARY KEY,
  observation_date   date        NOT NULL,
  underlying_symbol  text        NOT NULL,

  -- What kind of claim, and the number behind it.
  signal_family      text        NOT NULL,
  signal_name        text        NOT NULL,
  signal_value       numeric(14,6),
  -- Standardised against the signal's own history. Null until there is enough
  -- history to standardise against, rather than zero.
  signal_zscore      numeric(12,4),
  history_days       smallint,

  -- The contract, where the signal is about one. Null for a signal about the
  -- whole surface or the market.
  expiry             date,
  strike             numeric(14,4),
  option_type        text,
  dte_days           smallint,
  moneyness          numeric(12,6),
  implied_volatility numeric(10,4),

  -- The condition it was seen in, copied so a study can filter without a join.
  atm_iv_30d         numeric(10,4),
  realised_vol_20d   numeric(10,4),
  risk_reversal_30d  numeric(10,4),
  skew_agreement     numeric(6,4),
  oi_pcr             numeric(10,4),

  -- What it would have been entered at, if it were entered. A close, not a
  -- fill: see the outcome table.
  entry_close        numeric(14,4),
  entry_spot         numeric(14,4),

  quality_flags      text[]      NOT NULL DEFAULT '{}',
  signal_version     text        NOT NULL,
  built_at           timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT option_signal_type_chk
    CHECK (option_type IS NULL OR option_type IN ('CE', 'PE'))
);

CREATE INDEX IF NOT EXISTS option_signal_family_date_idx
  ON public.option_signal_observation (signal_family, observation_date);
CREATE INDEX IF NOT EXISTS option_signal_family_z_idx
  ON public.option_signal_observation (signal_family, signal_zscore);
CREATE INDEX IF NOT EXISTS option_signal_underlying_date_idx
  ON public.option_signal_observation (underlying_symbol, observation_date);


CREATE TABLE IF NOT EXISTS public.option_signal_outcome (
  signal_id             text      PRIMARY KEY
                        REFERENCES public.option_signal_observation (signal_id)
                        ON DELETE CASCADE,
  observation_date      date      NOT NULL,

  -- Option returns, close to close.
  option_return_1d_pct  numeric(12,4),
  option_return_2d_pct  numeric(12,4),
  option_return_5d_pct  numeric(12,4),
  -- Best and worst the option marked at over the horizon, from daily highs and
  -- lows. Not what a trade would have got: the path inside a day is unknown.
  mfe_5d_pct            numeric(12,4),
  mae_5d_pct            numeric(12,4),

  underlying_return_1d_pct numeric(12,4),
  underlying_return_5d_pct numeric(12,4),
  iv_change_1d          numeric(12,4),
  iv_change_5d          numeric(12,4),

  -- Realised volatility over the horizon AFTER the signal. This is the column
  -- that must never appear in a state or signal row: it is the answer, and a
  -- condition selected using it would describe an edge nobody could trade.
  forward_realised_vol_5d numeric(10,4),
  -- Implied at the signal minus what actually followed. The variance risk
  -- premium, in the only place it can honestly live.
  variance_premium_5d   numeric(12,4),

  horizon_days_available smallint NOT NULL,

  -- Not a number, a label, and it travels with the row rather than sitting in
  -- documentation. Bhavcopy has no bid or ask, so every return here is marked
  -- to a close. Spread, slippage and fees are not deducted because they are not
  -- known, and a return that has not paid them is not alpha.
  return_basis          text      NOT NULL DEFAULT 'eod_mark',
  outcome_version       text      NOT NULL,
  built_at              timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT option_signal_outcome_basis_chk
    CHECK (return_basis IN ('eod_mark', 'executable'))
);

CREATE INDEX IF NOT EXISTS option_signal_outcome_date_idx
  ON public.option_signal_outcome (observation_date);

ALTER TABLE public.option_signal_observation ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.option_signal_outcome ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.option_signal_observation FROM anon, authenticated;
REVOKE ALL ON public.option_signal_outcome FROM anon, authenticated;

COMMENT ON TABLE public.option_signal_observation IS
  'A claim made on a date from what was knowable then. Never contains an '
  'outcome: the forward columns live in option_signal_outcome.';
COMMENT ON COLUMN public.option_signal_outcome.return_basis IS
  'eod_mark: marked to closing prices, with no spread, slippage or fees '
  'deducted, because bhavcopy carries no bid or ask. Not realised alpha.';
