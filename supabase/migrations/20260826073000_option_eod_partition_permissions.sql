-- The partition helper could not run: "permission denied for schema public".
--
-- ensure_option_eod_partition creates a table, and creating one needs CREATE on
-- schema public. The function was SECURITY INVOKER, so it ran as service_role,
-- which does not hold that on a current Supabase project. The ingest derived
-- all 828 rows correctly and then failed at the write.
--
-- Two changes, belt and braces, because a research warehouse should not stop at
-- midnight on the first of a month.

-- 1. Partitions for a wide range up front. An empty partition costs a catalog
--    row, so pre-creating four years is cheaper than any runtime DDL. Bhavcopy
--    history reaches back years, so the range opens well before today.
DO $$
DECLARE
  month_start date := date '2024-01-01';
  part text;
BEGIN
  WHILE month_start < date '2028-01-01' LOOP
    part := format('option_eod_observation_%s', to_char(month_start, 'YYYYMM'));
    IF NOT EXISTS (SELECT 1 FROM pg_class WHERE relname = part) THEN
      EXECUTE format(
        'CREATE TABLE public.%I PARTITION OF public.option_eod_observation '
        'FOR VALUES FROM (%L) TO (%L)',
        part, month_start, (month_start + interval '1 month')::date);
    END IF;
    month_start := (month_start + interval '1 month')::date;
  END LOOP;
END;
$$;

-- 2. The helper still exists for a month beyond that range, and now runs as its
--    owner rather than the caller. SECURITY DEFINER is the reason the grants
--    below are tight: it must not be reachable by anon or authenticated.
--    search_path is pinned so the function cannot be steered at a different
--    schema by whatever the caller happens to have set.
CREATE OR REPLACE FUNCTION public.ensure_option_eod_partition(target date)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
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

REVOKE ALL ON FUNCTION public.ensure_option_eod_partition(date) FROM public;
REVOKE ALL ON FUNCTION public.ensure_option_eod_partition(date) FROM anon, authenticated;
GRANT EXECUTE ON FUNCTION public.ensure_option_eod_partition(date) TO service_role;

COMMENT ON FUNCTION public.ensure_option_eod_partition(date) IS
  'Creates the monthly partition for a date if absent. SECURITY DEFINER because '
  'creating a partition needs CREATE on schema public, which service_role does '
  'not hold; execute is granted to service_role only.';
