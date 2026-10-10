/**
 * Node-side wake timer for Continuous Gather → Learn + Institutional Scheduler morning DAG.
 * Engine also runs an internal loop; this keeps the pipeline warm across Render sleeps.
 * Never on the Ask request path.
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

function enabled() {
  // Heavy gather/learn work must be explicitly enabled on a dedicated worker;
  // it must never start by default in the public API process.
  return String(process.env.CONTINUOUS_GATHER_LEARN_SCHEDULER || 'false').toLowerCase() === 'true';
}

export function getContinuousGatherLearnSchedulerStatus() {
  return {
    enabled: Boolean(scheduler),
    lastRun,
    intervalMs: Number(process.env.CONTINUOUS_GATHER_LEARN_NODE_INTERVAL_MS || 30 * 60 * 1000),
  };
}

async function enginePost(path, body = {}) {
  const { baseUrl, token } = engineConfig();
  const response = await fetch(`${baseUrl}${path}`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(300_000),
  });
  const data = await response.json().catch(() => ({}));
  return { ok: response.ok, status: response.status, data };
}

export async function triggerContinuousGatherLearn({ forceMorningDag = false } = {}) {
  const hourUtc = new Date().getUTCHours();
  // Approx IST morning window (UTC 00:30–03:30 ≈ IST 06:00–09:00)
  const istMorning = hourUtc >= 0 && hourUtc < 4;
  const steps = [];

  if (forceMorningDag || (istMorning && String(process.env.CONTINUOUS_MORNING_DAG || 'false').toLowerCase() === 'true')) {
    try {
      const dag = await enginePost('/v1/scheduler/run', { dry_run: false, parallel: true });
      steps.push({ step: 'morning_dag', ok: dag.ok, status: dag.status });
    } catch (error) {
      steps.push({ step: 'morning_dag', ok: false, error: error.message });
    }
  }

  try {
    const cgl = await enginePost('/v1/continuous-gather-learn/run', {
      force_morning_dag: false,
      include_faa: String(process.env.CONTINUOUS_FAA_REFRESH || 'false').toLowerCase() === 'true',
    });
    steps.push({
      step: 'cgl_cycle',
      ok: cgl.ok,
      status: cgl.status,
      runId: cgl.data?.run_id || null,
      slot: cgl.data?.slot || null,
    });
  } catch (error) {
    steps.push({ step: 'cgl_cycle', ok: false, error: error.message });
  }

  lastRun = {
    at: new Date().toISOString(),
    ok: steps.some((s) => s.ok),
    steps,
  };
  if (lastRun.ok) {
    console.info('[cgl-scheduler] cycle complete', JSON.stringify(steps));
  } else {
    console.warn('[cgl-scheduler] cycle soft-failed', JSON.stringify(steps));
  }
  return lastRun;
}

export function startContinuousGatherLearnScheduler() {
  if (scheduler) return;
  if (!enabled()) {
    console.info('[cgl-scheduler] disabled (CONTINUOUS_GATHER_LEARN_SCHEDULER=false)');
    return;
  }
  const intervalMs = Number(process.env.CONTINUOUS_GATHER_LEARN_NODE_INTERVAL_MS || 30 * 60 * 1000);
  const tick = () => {
    triggerContinuousGatherLearn().catch((error) => {
      console.warn('[cgl-scheduler] trigger failed:', error.message);
      lastRun = { at: new Date().toISOString(), ok: false, error: error.message };
    });
  };
  // Delay first tick so Node + engine can boot
  setTimeout(tick, 45_000);
  scheduler = setInterval(tick, intervalMs);
  scheduler.unref?.();
  console.info(`[cgl-scheduler] active every ${Math.round(intervalMs / 60000)}m`);
}
