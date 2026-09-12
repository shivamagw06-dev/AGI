-- Short 1–2 line updates shown on Market Intelligence → Activities rail.
CREATE TABLE IF NOT EXISTS public.market_activities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  body text NOT NULL,
  published boolean NOT NULL DEFAULT true,
  created_by uuid REFERENCES auth.users (id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT market_activities_body_len CHECK (
    char_length(btrim(body)) BETWEEN 1 AND 280
  )
);

CREATE INDEX IF NOT EXISTS market_activities_published_created_idx
  ON public.market_activities (published, created_at DESC);

ALTER TABLE public.market_activities ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS market_activities_public_read ON public.market_activities;
CREATE POLICY market_activities_public_read
  ON public.market_activities
  FOR SELECT
  TO anon, authenticated
  USING (published = true);

DROP POLICY IF EXISTS market_activities_admin_select_all ON public.market_activities;
CREATE POLICY market_activities_admin_select_all
  ON public.market_activities
  FOR SELECT
  TO authenticated
  USING (auth.uid() = 'c56e4d07-273c-49c9-86a5-a4445e687ece'::uuid);

DROP POLICY IF EXISTS market_activities_admin_insert ON public.market_activities;
CREATE POLICY market_activities_admin_insert
  ON public.market_activities
  FOR INSERT
  TO authenticated
  WITH CHECK (auth.uid() = 'c56e4d07-273c-49c9-86a5-a4445e687ece'::uuid);

DROP POLICY IF EXISTS market_activities_admin_update ON public.market_activities;
CREATE POLICY market_activities_admin_update
  ON public.market_activities
  FOR UPDATE
  TO authenticated
  USING (auth.uid() = 'c56e4d07-273c-49c9-86a5-a4445e687ece'::uuid)
  WITH CHECK (auth.uid() = 'c56e4d07-273c-49c9-86a5-a4445e687ece'::uuid);

DROP POLICY IF EXISTS market_activities_admin_delete ON public.market_activities;
CREATE POLICY market_activities_admin_delete
  ON public.market_activities
  FOR DELETE
  TO authenticated
  USING (auth.uid() = 'c56e4d07-273c-49c9-86a5-a4445e687ece'::uuid);

GRANT SELECT ON public.market_activities TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON public.market_activities TO authenticated;
