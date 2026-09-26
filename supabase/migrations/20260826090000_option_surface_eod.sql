-- One volatility surface per underlying, expiry and trading day.
--
-- A different grain from option_eod_observation, which is why it is a
-- different table: ATM volatility, skew and curvature describe an expiry, not
-- a contract. Writing them onto every row would repeat one value across a
-- thousand strikes and invite a study to average them by mistake.
--
-- Reconstructed rather than observed. Nothing here is quoted by the exchange;
-- each number is fitted from the strikes that actually traded, so the fit
-- quality travels with the row and a study can require agreement instead of
-- trusting a number that merely exists. That is the same discipline the
-- forward and the implied volatility already carry.

CREATE TABLE IF NOT EXISTS public.option_surface_eod (
  observation_date   date        NOT NULL,
  underlying_symbol  text        NOT NULL,
  expiry             date        NOT NULL,
  dte_days           smallint    NOT NULL,

  forward            numeric(14,4),
  forward_quality    text,

  -- The level: volatility at the money, read off the fitted smile at k = 0
  -- rather than taken from the nearest strike, which on a wide chain can sit
  -- well away from it.
  atm_iv             numeric(10,4),

  -- The wings, at 25 delta. Calls give the call wing and puts the put wing,
  -- each from its own side of the book where that side is liquid.
  call_25d_iv        numeric(10,4),
  put_25d_iv         numeric(10,4),

  -- Skew: positive means calls are richer than puts, which for an equity
  -- index is the unusual direction.
  risk_reversal      numeric(10,4),
  -- Curvature: how much the wings sit above the money.
  butterfly          numeric(10,4),
  -- Slope of the fitted smile at the money, in vol points per unit of
  -- log-moneyness. Signed the same way as risk_reversal but measured locally.
  atm_slope          numeric(12,4),

  -- What the fit was built from and how well it described it.
  fit_points         smallint    NOT NULL,
  fit_rmse           numeric(10,4),
  surface_quality    text        NOT NULL,

  source             text        NOT NULL DEFAULT 'nse_bhavcopy',
  pipeline_version   text        NOT NULL,
  pricing_version    text        NOT NULL,
  surface_version    text        NOT NULL,
  built_at           timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT option_surface_eod_quality_chk
    CHECK (surface_quality IN ('high', 'medium', 'low')),
  CONSTRAINT option_surface_eod_pkey
    PRIMARY KEY (observation_date, underlying_symbol, expiry)
);

-- A term-structure query walks expiries within a day; a time-series query
-- walks days within an expiry. Both are common, neither is served by the
-- primary key alone.
CREATE INDEX IF NOT EXISTS option_surface_eod_underlying_date_idx
  ON public.option_surface_eod (underlying_symbol, observation_date);
CREATE INDEX IF NOT EXISTS option_surface_eod_underlying_dte_idx
  ON public.option_surface_eod (underlying_symbol, dte_days, observation_date);

-- Research data, not user data. RLS on with no policy: anon and authenticated
-- read nothing, the service role bypasses it. Same posture as the observations.
ALTER TABLE public.option_surface_eod ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.option_surface_eod FROM anon, authenticated;

COMMENT ON TABLE public.option_surface_eod IS
  'Fitted EOD volatility surface per underlying/expiry. Reconstructed from '
  'traded strikes, not quoted: surface_quality and fit_rmse say how much to '
  'trust each row.';
COMMENT ON COLUMN public.option_surface_eod.risk_reversal IS
  'call_25d_iv - put_25d_iv. Negative is the usual equity-index direction: '
  'puts bid over calls.';
