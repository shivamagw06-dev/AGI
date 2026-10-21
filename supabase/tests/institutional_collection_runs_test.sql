-- Assertions for the collection run record.
--
-- The migration itself is the thing under test. The last time an institutional
-- migration shipped without one of these, a CHECK constraint allowed values the
-- application never writes and forbade every value it does - which would have
-- rejected writes in production while passing review. So each constraint here
-- is exercised in both directions: a row that must be accepted, and a row that
-- must be rejected.

begin;
select plan(21);

-- Shape --------------------------------------------------------------------
select has_table('public', 'institutional_collection_runs', 'the run table exists');
select has_view('public', 'institutional_collection_health', 'the freshness view exists');

select has_column('public', 'institutional_collection_runs', c, 'column ' || c)
from unnest(array[
  'started_at', 'finished_at', 'status', 'trigger', 'host',
  'sec_requests', 'sec_throttled', 'sec_throttle_pause_ms', 'sec_paced_wait_ms',
  'sec_circuit_trips', 'managers_attempted', 'managers_succeeded',
  'filings_ingested', 'holdings_rows', 'amendments_detected',
  'failures', 'retry_state', 'next_scheduled_at'
]) as c;

-- A run is openable before it has done anything ----------------------------
select lives_ok(
  $$insert into public.institutional_collection_runs (trigger) values ('schedule')$$,
  'a run can be opened with no counters, which is how every run starts'
);

-- The finish-consistency constraint, both directions -----------------------
select throws_ok(
  $$insert into public.institutional_collection_runs (status, finished_at)
    values ('running', now())$$,
  '23514',
  null,
  'a run still running cannot claim a finish time'
);

select throws_ok(
  $$insert into public.institutional_collection_runs (status) values ('success')$$,
  '23514',
  null,
  'a finished run must record when it finished'
);

select lives_ok(
  $$insert into public.institutional_collection_runs (status, finished_at)
    values ('success', now())$$,
  'a finished run with a finish time is accepted'
);

-- Counters that cannot be true ---------------------------------------------
select throws_ok(
  $$insert into public.institutional_collection_runs
      (status, finished_at, managers_attempted, managers_succeeded)
    values ('success', now(), 10, 11)$$,
  '23514',
  null,
  'more managers cannot succeed than were attempted'
);

-- Status vocabulary --------------------------------------------------------
select throws_ok(
  $$insert into public.institutional_collection_runs (status, finished_at)
    values ('green', now())$$,
  '23514',
  null,
  'an unknown status is rejected rather than stored'
);

-- Every status the recorder actually writes must be accepted. This is the
-- direction the asset_type incident failed in: a constraint that looked
-- reasonable and excluded the application's real vocabulary.
select lives_ok(
  format(
    $$insert into public.institutional_collection_runs (status, finished_at) values (%L, now())$$,
    s
  ),
  'the recorder can write status ' || s
) from unnest(array['success', 'partial', 'failed', 'aborted']) as s;

select lives_ok(
  format($$insert into public.institutional_collection_runs (trigger) values (%L)$$, t),
  'the recorder can write trigger ' || t
) from unnest(array['schedule', 'manual', 'backfill', 'test']) as t;

-- The view answers, and answers once ---------------------------------------
select is(
  (select count(*)::int from public.institutional_collection_health),
  1,
  'the health view returns exactly one row, so the CMS can read it without aggregation'
);

-- Exposure -----------------------------------------------------------------
select is(
  (select relrowsecurity from pg_class where oid = 'public.institutional_collection_runs'::regclass),
  true,
  'row level security is enabled on the run table'
);

select is(
  (select count(*)::int from information_schema.role_table_grants
    where table_name = 'institutional_collection_runs' and grantee in ('anon', 'authenticated')),
  0,
  'operational telemetry is not reachable by anon or authenticated roles'
);

select is(
  (select count(*)::int from pg_class c
    where c.oid = 'public.institutional_collection_health'::regclass
      and c.reloptions::text like '%security_invoker=true%'),
  1,
  'the health view is SECURITY INVOKER, so it cannot read past its caller'
);

select * from finish();
rollback;
