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

export async function getLiveAlphaWorkspace({ fetchImpl = globalThis.fetch, limit = 250, now = new Date() } = {}) {
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
  const signalCountByRun = new Map();
  for (const signal of signals) signalCountByRun.set(signal.run_id, (signalCountByRun.get(signal.run_id) || 0) + 1);
  const latestRunByEngine = new Map();
  for (const run of runs) if (!latestRunByEngine.has(run.engine)) latestRunByEngine.set(run.engine, run);
  const staleAfterSeconds = Math.max(300, Number(process.env.LIVE_ALPHA_STALE_AFTER_SECONDS || 15 * 60));
  const strategyHealth = Object.fromEntries(Object.keys(ENGINE_LABELS).map((engine) => {
    const run = latestRunByEngine.get(engine);
    const storedSignals = run ? signalCountByRun.get(run.id) || 0 : 0;
    const ageSeconds = run?.as_of ? Math.max(0, Math.floor((now.getTime() - Date.parse(run.as_of)) / 1000)) : null;
    const orphaned = Boolean(run && storedSignals === 0);
    return [engine, {
      status: !run ? 'never_run' : orphaned ? 'persistence_failed' : ageSeconds > staleAfterSeconds ? 'stale' : 'ready',
      latest_run_at: run?.as_of || null, latest_run_id: run?.id || null,
      stored_signals: storedSignals, age_seconds: ageSeconds, orphaned,
    }];
  }));
  const successfulRuns = [...latestRunByEngine.values()].filter((run) => (signalCountByRun.get(run.id) || 0) > 0);
  const latestSuccessfulAt = successfulRuns.map((run) => run.as_of).filter(Boolean).sort().at(-1) || null;
  const latestAgeSeconds = latestSuccessfulAt ? Math.max(0, Math.floor((now.getTime() - Date.parse(latestSuccessfulAt)) / 1000)) : null;
  const degradedEngines = Object.entries(strategyHealth).filter(([, health]) => health.status === 'persistence_failed').map(([engine]) => engine);
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
      equityRun ? query('equity_opportunity_signals', `select=symbol,signal,rank,score,return_20d,return_60d,relative_20d,relative_60d,volume_ratio,trend,volume_confirmation,risk,reasons,factors&strategy_run_id=eq.${equityRun.id}&signal=eq.research_candidate&order=score.desc&limit=250`, fetchImpl) : [],
    ]);
    groww = { readiness: 'ready', runs: latestRuns, sectors, equities };
  } catch (error) {
    if (error.status !== 404) throw error;
    groww = { readiness: 'database_setup_required', runs: [], sectors: [], equities: [] };
  }
  return {
    generated_at: new Date().toISOString(), research_only: true, execution_enabled: false,
    engines: ENGINE_LABELS,
    readiness: {
      status: degradedEngines.length ? 'persistence_degraded' : 'ready',
      migrations_required: [], degraded_engines: degradedEngines,
    },
    freshness: {
      latest_successful_at: latestSuccessfulAt,
      age_seconds: latestAgeSeconds,
      stale_after_seconds: staleAfterSeconds,
      stale: latestAgeSeconds === null || latestAgeSeconds > staleAfterSeconds,
    },
    strategy_health: strategyHealth,
    runs, groww,
    signals: signals.map((signal) => ({ ...signal, engine: runById.get(signal.run_id)?.engine || null, as_of: runById.get(signal.run_id)?.as_of || signal.created_at })),
  };
}

export { ENGINE_LABELS };
