/**
 * Upstox FII/DII → warehouse ingest via Market Intelligence Engine.
 * Shared by API route and daily EOD scheduler.
 */

export async function refreshUpstoxInstitutionalFlows({
  // Upstox market-insights FII/DII expects segment form NSE_EQ|CASH (not bare NSE_EQ).
  dataTypes = undefined,
  dataType = undefined,
  interval = '1D',
  from = undefined,
} = {}) {
  const { getMarketFiiDii } = await import('../providers/upstox.js');
  const pack = await getMarketFiiDii({ dataTypes, dataType, interval, from });

  const engineBase = process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL;
  const token = process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN;
  if (!engineBase || !token) {
    return {
      ok: false,
      status: 503,
      error: 'intelligence_engine_not_configured',
      upstox: pack,
      warehouse: null,
    };
  }

  const ingest = await fetch(`${String(engineBase).replace(/\/$/, '')}/v1/market-intelligence/flows/ingest`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    body: JSON.stringify({ ...pack, actor: 'upstox_institutional_flow_v2' }),
    signal: AbortSignal.timeout(120_000),
  });

  const text = await ingest.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: String(text || '').slice(0, 400) };
  }

  return {
    ok: ingest.ok,
    status: ingest.status,
    upstox: pack,
    warehouse: data,
    error: ingest.ok ? null : data?.error || `ingest_http_${ingest.status}`,
  };
}

function nextDate(date) { const value = new Date(`${date}T00:00:00Z`); value.setUTCDate(value.getUTCDate() + 1); return value.toISOString().slice(0, 10); }
export async function backfillUpstoxInstitutionalFlows({ from = '2026-04-01', interval = '1D', maxWindows = 12 } = {}) {
  const summary = { ok: true, from, interval, windows: 0, observations: 0, ingested: 0, errors: [] }; let cursor = from; const today = new Date().toISOString().slice(0, 10);
  for (let index = 0; index < Math.max(1, Math.min(24, Number(maxWindows) || 12)); index += 1) { const result = await refreshUpstoxInstitutionalFlows({ from: cursor, interval }); summary.windows += 1; const observations = result.upstox?.observations || []; summary.observations += observations.length; if (!result.ok) { summary.ok = false; summary.errors.push({ from: cursor, error: result.error }); break; } summary.ingested += Number(result.warehouse?.written ?? result.warehouse?.wrote ?? observations.length); const dates = observations.map((row) => row.observation_date).filter(Boolean).sort(); const latest = dates.at(-1); if (!latest || latest >= today) break; const upcoming = nextDate(latest); if (upcoming <= cursor) break; cursor = upcoming; }
  summary.completed_through = cursor; return summary;
}
