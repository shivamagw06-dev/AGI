-- Keep the completed-only evidence sample fast when newer outcomes are missing.
-- Applied to production on 8 October 2026; no outcome rows are modified.
SET lock_timeout = '1s';
SET statement_timeout = '25s';
CREATE INDEX IF NOT EXISTS live_alpha_outcomes_completed_evidence_idx
  ON public.live_alpha_signal_outcomes (due_at DESC, id DESC)
  WHERE status = 'completed';
