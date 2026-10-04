-- Matches the migration applied to production after EXPLAIN showed a full scan
-- and sort of roughly 2 million rows for the bounded evidence endpoint.
SET LOCAL lock_timeout = '3s';
SET LOCAL statement_timeout = '90s';
CREATE INDEX IF NOT EXISTS live_alpha_outcomes_evidence_order_idx
  ON public.live_alpha_signal_outcomes (due_at DESC, id DESC);
