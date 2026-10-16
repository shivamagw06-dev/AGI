-- An append-only record of what the Street believed, and when.
--
-- `consensus_metric_vintages` already holds a Capital IQ import, and it is
-- genuinely monthly for periods that have since closed: FY2024 carries twelve
-- distinct consensus dates. What it does not carry is history for the periods
-- anyone wants to forecast. FY2027 and FY2028 exist at exactly one date,
-- 2026-08-19, because they arrived in a single bulk export rather than through
-- repeated capture. A revision cannot be computed from one observation, so the
-- forward years -- the only ones that matter -- have no measurable revision.
--
-- That is not fixable in arrears. A vintage that was not captured on the day is
-- gone, and no later export reconstructs it, because vendors ship the current
-- cross-section rather than a history of their own past opinions. This table
-- therefore exists to be written to on a schedule from today, and never
-- overwritten.
--
-- Three disciplines are enforced here rather than left to the writer:
--
--  * The unique key includes consensus_date, so a re-run appends a new vintage
--    instead of replacing yesterday's. An UPSERT that silently overwrote the
--    prior row is exactly how a table ends up looking fresh while having lost
--    its history.
--  * fiscal_period_end is required alongside the label. Modine's fiscal year
--    ends in March, so its "FY2027" is mostly calendar 2026; five of the other
--    six names end in December. Joining on the label alone silently compares
--    different economic periods.
--  * Dispersion columns exist from the start. The Capital IQ import carries
--    mean only, which is why analyst dispersion and revision breadth cannot be
--    computed from it at all. Leaving them out again would repeat that.

CREATE TABLE IF NOT EXISTS consensus_vintage_ledger (
  id                  bigserial PRIMARY KEY,

  symbol              text        NOT NULL,
  company_name        text,
  metric              text        NOT NULL,
  fiscal_period       text        NOT NULL,
  -- Absolute, so a label is never the only thing tying a number to a period.
  fiscal_period_end   date        NOT NULL,

  -- The date the estimate was believed, not the date we happened to fetch it.
  consensus_date      date        NOT NULL,
  -- The date we fetched it. These differ whenever a vendor lags, and the gap
  -- is itself worth measuring.
  observed_at         timestamptz NOT NULL DEFAULT now(),

  mean_estimate       numeric(20,6),
  median_estimate     numeric(20,6),
  high_estimate       numeric(20,6),
  low_estimate        numeric(20,6),
  analyst_count       integer,
  upward_revisions    integer,
  downward_revisions  integer,

  currency            text        NOT NULL DEFAULT 'USD',
  unit                text        NOT NULL DEFAULT 'per_share',
  source              text        NOT NULL,
  extraction_method   text,
  confidence          numeric(5,4),

  CONSTRAINT consensus_vintage_dispersion_ordered CHECK (
    (low_estimate IS NULL OR high_estimate IS NULL OR low_estimate <= high_estimate)
    AND (analyst_count IS NULL OR analyst_count >= 0)
  ),
  -- A vintage is identified by what was believed, for what, on what day, per
  -- source. Two vendors may disagree on the same day and both rows are kept.
  CONSTRAINT consensus_vintage_identity UNIQUE
    (symbol, metric, fiscal_period, consensus_date, source)
);

COMMENT ON TABLE consensus_vintage_ledger IS
  'Append-only Street estimates. Never UPDATE or UPSERT over an existing '
  'vintage: the history is the asset, and it cannot be rebuilt after the fact.';
COMMENT ON COLUMN consensus_vintage_ledger.fiscal_period_end IS
  'Absolute period end. Modine ends in March; most peers end in December. '
  'Joining on the fiscal_period label alone compares different economic years.';

CREATE INDEX IF NOT EXISTS consensus_vintage_series_idx
  ON consensus_vintage_ledger (symbol, metric, fiscal_period, consensus_date DESC);
CREATE INDEX IF NOT EXISTS consensus_vintage_asof_idx
  ON consensus_vintage_ledger (consensus_date DESC);

-- Refuse the overwrite rather than trusting every future writer to remember.
CREATE OR REPLACE FUNCTION consensus_vintage_is_append_only()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION
    'consensus_vintage_ledger is append-only; % on vintage (%, %, %, %) rejected',
    TG_OP, OLD.symbol, OLD.metric, OLD.fiscal_period, OLD.consensus_date;
END;
$$;

DROP TRIGGER IF EXISTS consensus_vintage_no_update ON consensus_vintage_ledger;
CREATE TRIGGER consensus_vintage_no_update
  BEFORE UPDATE OR DELETE ON consensus_vintage_ledger
  FOR EACH ROW EXECUTE FUNCTION consensus_vintage_is_append_only();

ALTER TABLE consensus_vintage_ledger ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT ON consensus_vintage_ledger TO service_role;
GRANT USAGE, SELECT ON SEQUENCE consensus_vintage_ledger_id_seq TO service_role;
