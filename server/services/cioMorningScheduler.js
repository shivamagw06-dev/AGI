/**
 * CIO Desk morning scheduler — triggers Intelligence Engine via local proxy path.
 * Falls soft if the engine is down (deterministic briefing pages remain available).
 */

let scheduler = null;
let lastRun = null;

function engineConfig() {
  let baseUrl = (process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) {
    baseUrl = `https://${baseUrl}`;
  }
  const token = (process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim();
  return { baseUrl, token };
}

export function getCioSchedulerStatus() {
  return {
    enabled: Boolean(scheduler),
    lastRun,
    intervalMs: Number(process.env.CIO_MORNING_INTERVAL_MS || 30 * 60 * 1000),
  };
}

export async function triggerCioMorningRun({ force = false } = {}) {
  const { baseUrl, token } = engineConfig();
  const response = await fetch(`${baseUrl}/v1/research/runs`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    body: JSON.stringify({
      desk: 'cio_morning',
      force,
      metadata: { source: 'agi-node-scheduler', session: 'pre_market' },
    }),
    signal: AbortSignal.timeout(180_000),
  });
  const data = await response.json().catch(() => ({}));
  lastRun = {
    at: new Date().toISOString(),
    ok: response.ok,
    status: response.status,
    runId: data?.run_id || null,
  };
  if (!response.ok) {
    console.warn('[cio-morning] engine run failed:', response.status, data?.detail || data?.error || '');
  } else {
    console.info('[cio-morning] run complete:', data?.run_id, data?.status);
  }
  return data;
}

export function startCioMorningScheduler() {
  if (scheduler) return;
  // This invokes a full engine research run. Keep it opt-in until it lives on
  // an isolated worker, not alongside website traffic.
  if ((process.env.CIO_MORNING_SCHEDULER || 'false').toLowerCase() !== 'true') return;

  const intervalMs = Number(process.env.CIO_MORNING_INTERVAL_MS || 30 * 60 * 1000);
  const tick = () => {
    triggerCioMorningRun().catch((error) => {
      console.warn('[cio-morning] scheduled trigger failed:', error.message);
      lastRun = { at: new Date().toISOString(), ok: false, error: error.message };
    });
  };

  // Delay first tick so Node + engine can boot
  setTimeout(tick, 15_000);
  scheduler = setInterval(tick, intervalMs);
  scheduler.unref?.();
  console.info(`[cio-morning] scheduler active every ${Math.round(intervalMs / 60000)}m`);
}
