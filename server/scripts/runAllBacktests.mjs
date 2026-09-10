/**
 * Run the filing-aware backtest for every tracked manager.
 *
 *   node server/scripts/runAllBacktests.mjs
 *   node server/scripts/runAllBacktests.mjs --apply
 *   node server/scripts/runAllBacktests.mjs --apply --quarters 40 --top 10
 *
 * The Performance lab reads stored runs and computes one manager at a time.
 * That is right for a page and wrong for filling it: fifty managers behind a
 * browser request is fifty requests that each hold a connection open for
 * minutes.
 *
 * It also refreshes runs that are stale rather than wrong. A run stores the
 * verdict it reached under the rules and prices of the day it ran, and both
 * have changed: the coverage floor moved from 70% to 95%, and eleven years of
 * adjusted closes were loaded where there had been five. A manager stored as
 * not_calculable under the old prices may be calculable now, and nothing
 * re-examines that on its own.
 *
 * Every manager is attempted. A manager that still cannot clear the bar is
 * stored as not_calculable with its reasons, which is a result and not a
 * failure - the panel shows those reasons rather than a number.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { runInstitutionalBacktest, paged } from '../services/institutionalResearchLayerService.js';

const APPLY = process.argv.includes('--apply');
const argOf = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : null; };
const QUARTERS = Number(argOf('--quarters') || 20);
const TOP_N = Number(argOf('--top') || 10);
const ONLY = argOf('--manager');

if (!getSupabaseAdminCredentials()) {
  console.error('[backtests] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();
const started = Date.now();
const elapsed = () => ((Date.now() - started) / 1000).toFixed(0);
const pct = (value) => `${(Number(value || 0) * 100).toFixed(1)}%`;

async function main() {
  console.log(`[backtests] mode: ${APPLY ? 'APPLY - this writes' : 'dry run - nothing is written'}`);
  console.log(`[backtests] strategy: top ${TOP_N} by disclosed value, ${QUARTERS} quarters`);

  const managers = await paged(
    () => client.from('institutional_managers').select('id,slug,display_name').order('display_name'),
    { label: 'managers' },
  );
  const wanted = ONLY ? managers.filter((m) => m.slug === ONLY || m.id === ONLY) : managers;
  if (!wanted.length) throw new Error(ONLY ? `No manager matches ${ONLY}.` : 'No managers are tracked.');

  const stored = await paged(
    () => client.from('institutional_backtest_runs').select('manager_id,status,generated_at').order('manager_id').order('generated_at'),
    { label: 'stored runs' },
  );
  const latest = new Map();
  for (const row of stored) latest.set(row.manager_id, row); // ordered ascending, so the last wins
  const withRun = wanted.filter((m) => latest.has(m.id));
  const calculable = withRun.filter((m) => latest.get(m.id).status === 'calculated');

  console.log(`[backtests] ${wanted.length} manager(s); ${withRun.length} have a stored run, ${calculable.length} of those calculated`);

  if (!APPLY) {
    // Deliberately not an estimate in minutes. The first run of this script is
    // the only thing that can say how long a manager takes, and guessing was
    // wrong by a factor of three the last time this codebase estimated a job.
    console.log(`[backtests] would run ${wanted.length} manager(s). Each reads its filings, its holdings and their adjusted closes.`);
    console.log('[backtests] dry run only. Re-run with --apply to compute and write.');
    return;
  }

  const results = { calculated: 0, not_calculable: 0, failed: 0 };
  for (const [index, manager] of wanted.entries()) {
    const at = `${index + 1}/${wanted.length}`;
    try {
      const run = await runInstitutionalBacktest({ managerSlug: manager.slug, topN: TOP_N, quarters: QUARTERS });
      const metrics = run.metrics || {};
      if (run.status === 'calculated') {
        results.calculated += 1;
        console.log(`[backtests] ${at} ${manager.display_name}: ${pct(metrics.total_return)} vs SPY ${pct(metrics.spy_return)} `
          + `(excess ${pct(metrics.excess_vs_spy)}), ${metrics.periods} periods, ${pct(metrics.average_coverage)} priced  (${elapsed()}s)`);
      } else {
        results.not_calculable += 1;
        console.log(`[backtests] ${at} ${manager.display_name}: not calculable - ${metrics.reason || 'no reason recorded'}  (${elapsed()}s)`);
      }
    } catch (error) {
      // One manager failing must not end the sweep. The others are unaffected
      // and the failure is reported rather than swallowed.
      results.failed += 1;
      console.error(`[backtests] ${at} ${manager.display_name}: FAILED - ${error.message}`);
    }
  }

  console.log('');
  console.log(`[backtests] ${results.calculated} calculated, ${results.not_calculable} not calculable, ${results.failed} failed, in ${elapsed()}s`);
}

main().catch((error) => {
  console.error(`[backtests] ${error.message}`);
  process.exit(1);
});
