/**
 * Lightweight intelligence-engine health pings from the API process.
 * Runs when CMS ingest worker is external so keep-warm is not duplicated there.
 */

let started = false;

function engineConfig() {
  const baseUrl = String(process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
  const token = String(process.env.INTELLIGENCE_ENGINE_TOKEN || process.env.AGIB_SERVICE_TOKEN || '').trim();
  return { baseUrl, token };
}

async function pingEngine() {
  const { baseUrl, token } = engineConfig();
  if (!baseUrl) return;
  try {
    await fetch(`${baseUrl}/v1/health`, {
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${token}`,
        'X-AGI-Intelligence-Token': token,
      },
      signal: AbortSignal.timeout(20_000),
    });
  } catch {
    /* best-effort */
  }
}

export function startEngineKeepWarm() {
  if (started) return;
  const workerExternal = String(process.env.CMS_INGEST_WORKER_MODE || '').toLowerCase() === 'external';
  const ms = Number(process.env.ENGINE_KEEP_WARM_MS || (workerExternal ? process.env.CMS_INGEST_KEEP_WARM_MS : 0) || 5 * 60_000);
  if (ms <= 0) return;
  started = true;
  setInterval(pingEngine, ms);
  setTimeout(pingEngine, 30_000);
  console.info(`[engine-keep-warm] active (every ${Math.round(ms / 60000)}m)`);
}
