-- Optional durable mirror for KIP snapshots (Architecture v1.0.1 LOCKED — additive).
-- Used when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY are set on the intelligence engine.
-- Local disk snapshot remains primary; this survives Render Free ephemeral filesystem wipes.

CREATE TABLE IF NOT EXISTS public.kip_snapshots (
  id text PRIMARY KEY,
  saved_at timestamptz,
  stats jsonb NOT NULL DEFAULT '{}'::jsonb,
  payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  updated_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.kip_snapshots ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'kip_snapshots'
      AND policyname = 'kip_snapshots_service_only'
  ) THEN
    -- No anon/authenticated policies: service role bypasses RLS.
    CREATE POLICY kip_snapshots_service_only
      ON public.kip_snapshots
      FOR ALL
      TO authenticated
      USING (false)
      WITH CHECK (false);
  END IF;
END $$;
