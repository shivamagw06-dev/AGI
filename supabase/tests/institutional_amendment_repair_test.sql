-- Assertions for the amendment repair audit trail.
--
-- The archive is the only record of what holdings looked like before a repair
-- overwrote them, so the properties that matter are that it can hold a row
-- whatever the holdings schema does later, and that the reconciliation report
-- cannot record an outcome nobody can interpret.

begin;
select plan(12);

select has_table('public', 'institutional_holdings_archive', 'the pre-repair archive exists');
select has_table('public', 'institutional_amendment_repairs', 'the reconciliation table exists');
select has_view('public', 'institutional_amendment_repair_summary', 'the run summary view exists');

-- The archive keeps the row whole.
select col_type_is('public', 'institutional_holdings_archive', 'holding', 'jsonb',
  'the archived holding is stored as jsonb, so a later holdings schema change cannot make it unreadable');

select lives_ok(
  $$insert into public.institutional_holdings_archive (accession_number, holding)
    values ('0000902664-25-003078', '{"cusip":"037833100","shares":1000}'::jsonb)$$,
  'a holding can be archived with only the fields it actually had'
);

-- Every outcome the job can produce must be storable. The asset_type incident
-- in miniature: a constraint that excludes the caller's real vocabulary.
select lives_ok(
  format($$insert into public.institutional_amendment_repairs
    (repair_run_id, accession_number, outcome) values (gen_random_uuid(), 'X', %L)$$, o),
  'the reconciliation table accepts outcome ' || o
) from unnest(array['repaired', 'unchanged', 'needs_review', 'failed', 'would_repair']) as o;

select throws_ok(
  $$insert into public.institutional_amendment_repairs
    (repair_run_id, accession_number, outcome) values (gen_random_uuid(), 'X', 'probably_fine')$$,
  '23514',
  null,
  'an outcome nobody can interpret is rejected rather than stored'
);

-- The summary distinguishes a dry run from an applied one.
select is(
  (select count(*)::int from information_schema.columns
    where table_name = 'institutional_amendment_repair_summary' and column_name = 'applied'),
  1,
  'the run summary states whether the run was applied, so a dry run cannot be mistaken for a repair'
);

select is(
  (select count(*)::int from information_schema.role_table_grants
    where table_name in ('institutional_holdings_archive', 'institutional_amendment_repairs')
      and grantee in ('anon', 'authenticated')),
  0,
  'the audit trail is not reachable by anon or authenticated roles'
);

select * from finish();
rollback;
