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
  if (!response.ok) throw new Error(`Alpha workspace query failed (${response.status}).`);
  return response.json();
}

export async function getLiveAlphaWorkspace({ fetchImpl = globalThis.fetch, limit = 250 } = {}) {
  const runs = await query('live_alpha_runs', `select=id,engine,as_of,market_session,universe_size,diagnostics&order=as_of.desc&limit=25`, fetchImpl);
  const runIds = runs.map((run) => run.id);
  const signals = runIds.length ? await query(
    'live_alpha_signals',
    `select=id,run_id,symbol,sector,rank,classification,alpha_z,signal_quality_score,signal_quality_label,empirical_confidence_score,comparable_observations,liquidity_ok,factor_values,direction,price_at_signal,nifty_at_signal,sector_at_signal,volume_ratio,vwap_deviation,oi_change,created_at&run_id=in.(${runIds.join(',')})&order=created_at.desc&limit=${Math.min(500, Math.max(1, limit))}`,
    fetchImpl,
  ) : [];
  const runById = new Map(runs.map((run) => [run.id, run]));
  return {
    generated_at: new Date().toISOString(), research_only: true, execution_enabled: false,
    engines: ENGINE_LABELS,
    runs,
    signals: signals.map((signal) => ({ ...signal, engine: runById.get(signal.run_id)?.engine || null, as_of: runById.get(signal.run_id)?.as_of || signal.created_at })),
  };
}

export { ENGINE_LABELS };
