/**
 * Dedicated CMS intelligence ingest worker.
 *
 * Deploy as a Render Background Worker (recommended on Starter+), or run locally:
 *   CMS_INGEST_IS_WORKER=1 node server/workers/cmsIngestWorker.js
 *
 * When using this process, set on the API web service:
 *   CMS_INGEST_WORKER_MODE=external
 * so the API only enqueues and does not double-process.
 */

import 'dotenv/config';

process.env.CMS_INGEST_IS_WORKER = '1';

function engineConfig() {
  let baseUrl = (process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) {
    baseUrl = `https://${baseUrl}`;
  }
  const token = (process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim();
  return { baseUrl, token };
}

async function engineFetch(path, { method = 'GET', body = null, timeoutMs = 120_000 } = {}) {
  const { baseUrl, token } = engineConfig();
  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      'X-AGI-Intelligence-Token': token,
    },
    body: body ? JSON.stringify(body) : undefined,
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await response.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  return { ok: response.ok, status: response.status, data };
}

const { startCmsIngestJobWorker, reclaimStalledJobs, getWorkerInfo } = await import(
  '../services/cmsIngestJobs.js'
);

const started = startCmsIngestJobWorker(engineFetch, { force: true });
const reclaimed = await reclaimStalledJobs();
console.info('[cms-ingest-worker] online', {
  ...getWorkerInfo(),
  started,
  reclaimed,
  engine: engineConfig().baseUrl,
});

// Keep process alive; tick loop is inside startCmsIngestJobWorker.
setInterval(() => {
  /* heartbeat no-op — intervals in worker service keep the event loop alive */
}, 60_000);
