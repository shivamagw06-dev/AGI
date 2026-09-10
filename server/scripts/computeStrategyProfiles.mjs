/**
 * Derive each manager's strategy from its book.
 *
 *   node server/scripts/computeStrategyProfiles.mjs
 *   node server/scripts/computeStrategyProfiles.mjs --apply
 *
 * No network at all. Every number comes from holdings already stored, measured
 * in SQL by institutional_strategy_metrics() because the alternative is pulling
 * roughly ninety thousand holding rows through PostgREST to count them here -
 * which is both slow and the exact shape of the row-cap bug this codebase has
 * hit a dozen times.
 *
 * The classification is in strategyFingerprint.js and is a pure function of the
 * measurements, so it is tested against the real books rather than against
 * numbers invented to suit it.
 *
 * Prints a table in dry-run so the labels can be read before they are written.
 * A label that looks wrong on a manager you know is the point of the dry run.
 */
import { createSupabaseAdmin, getSupabaseAdminCredentials } from '../lib/supabaseAdmin.js';
import { strategyProfile } from '../services/strategyFingerprint.js';

const APPLY = process.argv.includes('--apply');

if (!getSupabaseAdminCredentials()) {
  console.error('[strategy] SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.');
  process.exit(78);
}
const client = createSupabaseAdmin();

const num = (value) => (value === null || value === undefined ? null : Number(value));

/** The database column names, turned into what the classifier expects. */
function metricsOf(row) {
  return {
    positions: num(row.positions),
    priorPositions: num(row.prior_positions),
    quartersObserved: num(row.quarters_observed),
    top10Pct: num(row.top10_pct),
    optionsPct: num(row.options_pct),
    votesPct: num(row.votes_pct),
    turnoverPct: num(row.turnover_pct),
    medianQuartersHeld: row.median_quarters_held === null ? null
      : Math.round(Number(row.median_quarters_held)),
    topSector: row.top_sector || null,
    topSectorPct: num(row.top_sector_pct),
    activistFilings: num(row.activist_filings) || 0,
    passiveFilings: num(row.passive_filings) || 0,
  };
}

async function main() {
  // Fifty-one managers today. Bounded rather than assumed: an rpc() that
  // outgrows a thousand rows would silently return the first thousand, and
  // asking for one more than the limit is how that is noticed instead.
  const LIMIT = 1000;
  const { data, error } = await client.rpc('institutional_strategy_metrics')
    .limit(LIMIT + 1);
  if (error) throw new Error(`measuring: ${error.message}`);
  const rows = data || [];
  if (rows.length > LIMIT) {
    throw new Error(`${rows.length} managers measured, above the ${LIMIT} this script reads in one call`);
  }
  console.log(`[strategy] measured ${rows.length} manager book(s)`);

  const written = [];
  const skipped = [];
  for (const row of rows) {
    const metrics = metricsOf(row);
    const profile = strategyProfile(metrics);
    if (!profile) { skipped.push(row.display_name); continue; }
    written.push({
      manager_id: row.manager_id,
      archetype: profile.archetype,
      label: profile.label,
      characteristic_of: profile.characteristicOf,
      confidence: profile.confidence,
      evidence: profile.evidence,
      traits: profile.traits,
      caveats: profile.caveats,
      metrics,
      as_of_date: row.as_of_date,
      quarters_observed: metrics.quartersObserved || 0,
      computed_at: new Date().toISOString(),
      display_name: row.display_name,
    });
  }

  const pad = (value, width) => String(value ?? '-').padEnd(width);
  console.log('');
  console.log(`${pad('manager', 38)}${pad('archetype', 24)}${pad('conf', 8)}${pad('pos', 7)}${pad('top10', 8)}${pad('turn', 8)}traits`);
  for (const row of written) {
    const m = row.metrics;
    console.log(
      pad(row.display_name.slice(0, 36), 38)
      + pad(row.archetype, 24)
      + pad(row.confidence, 8)
      + pad(m.positions, 7)
      + pad(m.top10Pct === null ? '-' : `${m.top10Pct}%`, 8)
      + pad(m.turnoverPct === null ? 'n/a' : `${m.turnoverPct}%`, 8)
      + row.traits.map((t) => t.key).join(', '),
    );
  }
  if (skipped.length) {
    console.log('');
    console.log(`[strategy] no book to classify: ${skipped.join(', ')}`);
  }

  const unmeasurable = written.filter((row) => row.metrics.turnoverPct === null);
  if (unmeasurable.length) {
    console.log('');
    // Turnover is null rather than zero for these, so nothing reads them as
    // "changed nothing". They need a second stored quarter, not a fix.
    console.log(`[strategy] turnover not yet measurable for ${unmeasurable.length}: `
      + `${unmeasurable.map((row) => row.display_name).join(', ')}`);
  }

  if (!APPLY) {
    console.log('');
    console.log('[strategy] dry run only. Re-run with --apply to write.');
    return;
  }

  const payload = written.map(({ display_name: _ignored, ...rest }) => rest);
  for (let index = 0; index < payload.length; index += 200) {
    const { error: writeError } = await client
      .from('institutional_manager_strategy_profiles')
      .upsert(payload.slice(index, index + 200), { onConflict: 'manager_id' });
    if (writeError) throw new Error(`writing at ${index}: ${writeError.message}`);
  }
  console.log(`[strategy] ${payload.length} profile(s) written`);
}

main().catch((error) => {
  console.error(`[strategy] ${error.message}`);
  process.exit(1);
});
