/**
 * Reclaim disk from live_market_snapshots.
 *
 *   node server/scripts/pruneLiveSnapshots.mjs              # dry run, writes nothing
 *   node server/scripts/pruneLiveSnapshots.mjs --apply
 *   node server/scripts/pruneLiveSnapshots.mjs --apply --max-minutes 20
 *
 * The table is 4.4 GB and grows about 150 MB a day with nothing pruning it.
 * A full disk puts Postgres into read-only, which takes the site down, so the
 * point of this is keeping the database writable.
 *
 * Two steps, both defined in server/services/snapshotRetention.js against what
 * actually reads the table. Rows past the longest reader are deleted; rows
 * past ninety minutes have raw_factors - most of the row's weight - emptied.
 * live_alpha_signals is deliberately never touched: its outcomes reference it
 * `on delete cascade`, and those outcomes are the only record of whether the
 * strategy engines worked.
 *
 * Work is day-sized and oldest-first. One statement across four million rows
 * builds a temp and WAL footprint large enough to exhaust the disk it is
 * trying to save - which is exactly what happened when this table was last
 * scanned in one pass.
 *
 * Space caveat: neither step returns space to the operating system. Postgres
 * marks the freed pages reusable, so the table stops growing but does not
 * shrink on disk. `vacuum full public.live_market_snapshots;` is what shrinks
 * it, and it needs free space equal to the surviving data and takes an
 * exclusive lock - so run it after this, when the survivors are small.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import {
  dayWindows, refuseReason, plannedSteps, RAW_FACTORS_KEEP_DAYS, ROW_KEEP_DAYS,
} from '../services/snapshotRetention.js';

const TABLE = 'live_market_snapshots';
const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const MAX_MINUTES = Number(argOf('--max-minutes')) || 30;

if (!getSupabaseAdminCredentials()) {
  console.error('[prune] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(1);
const overCeiling = () => Date.now() - started > MAX_MINUTES * 60_000;

/**
 * Bounds and counts, computed in the database.
 *
 * These were read through PostgREST first and hit `canceling statement due to
 * statement timeout`: the REST role's timeout is short, and an exact count
 * over four million rows does not fit inside it however the query is shaped.
 * The report function raises the timeout for its own duration and returns the
 * whole thing in one round trip.
 */
async function report() {
  const { data, error } = await client.rpc('live_snapshot_retention_report', {
    raw_days: RAW_FACTORS_KEEP_DAYS,
    row_days: ROW_KEEP_DAYS,
  });
  if (error) throw new Error(`reading the retention report: ${error.message}`);
  if (!data) throw new Error('the retention report returned nothing');
  return data;
}

const gb = (bytes) => `${(Number(bytes) / 1024 ** 3).toFixed(2)} GB`;

async function main() {
  const asOf = new Date();
  const facts = await report();
  const { oldest, newest } = facts;

  if (!oldest || !newest) {
    console.log('[prune] the table is empty; nothing to do.');
    return;
  }

  console.log(`[prune] ${TABLE}: ${gb(facts.table_bytes)} on disk, about ${Number(facts.estimated_rows).toLocaleString()} rows`);
  console.log(`[prune] oldest ${oldest}  newest ${newest}`);
  console.log(`[prune] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);

  // The counts come from the database's own `now()`, so the windows are built
  // from the database's cutoffs too. Taking one from SQL and the other from
  // this process would leave the reported count describing a slightly
  // different set of rows than the one the loop actually walks.
  const fromDb = { delete: facts.row_cutoff, 'blank-factors': facts.raw_cutoff };
  const counts = {
    delete: Number(facts.deletable_rows) || 0,
    'blank-factors': Number(facts.blankable_rows) || 0,
  };
  const steps = plannedSteps(asOf).map((step) => ({
    ...step,
    cutoffAt: fromDb[step.name] ? new Date(fromDb[step.name]).toISOString() : step.cutoffAt,
  }));

  // Every step is checked before any step writes. A refusal means something
  // upstream miscomputed, and finding that out after the first delete has
  // already run is worth nothing.
  for (const step of steps) {
    const refusal = refuseReason({ cutoffAt: step.cutoffAt, newest, asOf });
    if (refusal) {
      console.error(`[prune] refusing ${step.name}: ${refusal}`);
      process.exitCode = 1;
      return;
    }
  }

  let floor = oldest;
  for (const step of steps) {
    const windows = dayWindows(floor, step.cutoffAt);
    console.log(
      `\n[prune] ${step.name}: ${step.describes}`
      + `\n        cutoff ${step.cutoffAt}`
      + `\n        ${counts[step.name].toLocaleString()} rows to touch, ${windows.length} day-sized batches`,
    );

    if (!APPLY) {
      // The floor still advances so the second step's window list reflects the
      // rows the first step would already have removed.
      floor = step.cutoffAt;
      continue;
    }

    let touched = 0;
    for (const window of windows) {
      if (overCeiling()) {
        console.log(`[prune] ${step.name}: stopping at the ${MAX_MINUTES}-minute ceiling; re-run to continue.`);
        break;
      }
      const { data, error } = await client.rpc(step.rpc, { from_at: window.from, to_at: window.to });
      if (error) throw new Error(`${step.rpc} ${window.from}..${window.to}: ${error.message}`);
      const rows = Number(data) || 0;
      touched += rows;
      console.log(`[prune]   ${window.from.slice(0, 10)}  ${rows.toLocaleString()} rows  (${elapsed()}s)`);
    }
    console.log(`[prune] ${step.name}: ${touched.toLocaleString()} rows touched`);
    floor = step.cutoffAt;
  }

  if (!APPLY) {
    console.log('\n[prune] dry run only. Re-run with --apply to write.');
  } else {
    const after = await report();
    console.log(`\n[prune] done. ${gb(after.table_bytes)} on disk - unchanged or larger is expected here:`);
    console.log('[prune] the freed pages are reusable but not returned to the OS. To shrink the file, run');
    console.log('[prune]   vacuum full public.live_market_snapshots;');
    console.log('[prune] in the SQL editor. It needs free space equal to the survivors and takes an exclusive lock.');
  }
}

main().catch((err) => {
  console.error(`[prune] ${err.message}`);
  process.exit(1);
});
