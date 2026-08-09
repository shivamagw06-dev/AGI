const ENGINE_LABELS = Object.freeze({
  cross_sectional_momentum_v1: 'Leadership',
  volume_liquidity_anomaly_v1: 'Activity',
  opening_range_expansion_v1: 'Breakout',
  intraday_mean_reversion_v1: 'Dislocation',
  derivatives_positioning_v1: 'Positioning',
});

function credentials() {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  return url && key ? { url, key } : null;
}

async function query(table, search, fetchImpl) {
  const auth = credentials();
  if (!auth) return [];
  const response = await fetchImpl(`${auth.url}/rest/v1/${table}?${search}`, {
    headers: { apikey: auth.key, Authorization: `Bearer ${auth.key}` },
  });
  if (!response.ok) {
    const error = new Error(`Alpha workspace query failed (${response.status}).`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export async function getLiveAlphaWorkspace({ fetchImpl = globalThis.fetch, limit = 250 } = {}) {
  let runs;
  try {
    runs = await query('live_alpha_runs', `select=id,engine,as_of,market_session,universe_size,diagnostics&order=as_of.desc&limit=25`, fetchImpl);
  } catch (error) {
    if (error.status !== 404) throw error;
    return {
      generated_at: new Date().toISOString(), research_only: true, execution_enabled: false,
      engines: ENGINE_LABELS, runs: [], signals: [],
      readiness: { status: 'database_setup_required', migrations_required: ['20260809150000_live_alpha_engine.sql', '20260809160000_live_alpha_outcomes.sql', '20260809170000_upstox_live_market_feed.sql', '20260809180000_live_alpha_volume_baselines.sql', '20260809190000_live_alpha_strategy_classifications.sql'] },
    };
  }
  const runIds = runs.map((run) => run.id);
  const signals = runIds.length ? await query(
    'live_alpha_signals',
    `select=id,run_id,symbol,instrument_key,sector,rank,classification,alpha_z,signal_quality_score,signal_quality_label,empirical_confidence_score,comparable_observations,liquidity_ok,factor_values,direction,market_regime,price_at_signal,nifty_at_signal,sector_at_signal,volume_ratio,vwap_deviation,oi_change,created_at&run_id=in.(${runIds.join(',')})&order=created_at.desc&limit=${Math.min(500, Math.max(1, limit))}`,
    fetchImpl,
  ) : [];
  const runById = new Map(runs.map((run) => [run.id, run]));
  let groww = { readiness: 'ready', runs: [], sectors: [], equities: [] };
  try {
    const growwRuns = await query('research_strategy_runs', 'select=id,strategy,run_id,as_of,received_at,status,coverage,error_count&order=as_of.desc&limit=10', fetchImpl);
    const latestByStrategy = new Map();
    for (const run of growwRuns) if (!latestByStrategy.has(run.strategy)) latestByStrategy.set(run.strategy, run);
    const latestRuns = [...latestByStrategy.values()];
    const sectorRun = latestByStrategy.get('agi_sector_rotation_v1');
    const equityRun = latestByStrategy.get('agi_equity_opportunity_v1');
    const [sectors, equities] = await Promise.all([
      sectorRun ? query('sector_rotation_signals', `select=sector,rank,score,return_5d,return_20d,relative_20d,relative_60d,rotation,risk,factors&strategy_run_id=eq.${sectorRun.id}&order=rank.asc&limit=20`, fetchImpl) : [],
      equityRun ? query('equity_opportunity_signals', `select=symbol,signal,rank,score,return_20d,return_60d,relative_20d,relative_60d,volume_ratio,trend,volume_confirmation,risk,reasons,factors&strategy_run_id=eq.${equityRun.id}&order=score.desc&limit=30`, fetchImpl) : [],
    ]);
    groww = { readiness: 'ready', runs: latestRuns, sectors, equities };
  } catch (error) {
    if (error.status !== 404) throw error;
    groww = { readiness: 'database_setup_required', runs: [], sectors: [], equities: [] };
  }
  return {
    generated_at: new Date().toISOString(), research_only: true, execution_enabled: false,
    engines: ENGINE_LABELS,
    readiness: { status: 'ready', migrations_required: [] }, runs, groww,
    signals: signals.map((signal) => ({ ...signal, engine: runById.get(signal.run_id)?.engine || null, as_of: runById.get(signal.run_id)?.as_of || signal.created_at })),
  };
}

export { ENGINE_LABELS };
