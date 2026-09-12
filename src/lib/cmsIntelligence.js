import { API_ORIGIN } from '@/config';

function stripHtml(html = '') {
  return String(html)
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Allowlisted equity tickers only — never scrape prose into fake tickers. */
const KNOWN_TICKERS = new Set([
  'ICICIBANK',
  'HDFCBANK',
  'RELIANCE',
  'TCS',
  'INFY',
  'SBIN',
  'AXISBANK',
  'KOTAKBANK',
  'BHARTIARTL',
  'LT',
  'ITC',
  'WIPRO',
  'MARUTI',
  'TATAMOTORS',
  'HINDUNILVR',
  'HCLTECH',
  'TECHM',
  'LTIM',
  'LTTS',
  'PERSISTENT',
  'COFORGE',
  'MPHASIS',
  'OFSS',
  'AAPL',
  'MSFT',
  'GOOGL',
  'AMZN',
  'NVDA',
]);

const TICKER_BLOCK = new Set([
  'THE',
  'AND',
  'FOR',
  'WITH',
  'FROM',
  'THIS',
  'THAT',
  'HAVE',
  'WILL',
  'INTO',
  'OVER',
  'UNDER',
  'INDIA',
  'INDIAN',
  'MARKET',
  'MARKETS',
  'STOCK',
  'STOCKS',
  'SECTOR',
  'UPDATE',
  'OUTLOOK',
  'REVIEW',
  'GROWTH',
  'WEAK',
  'DEAL',
  'DEALS',
  'SERVICE',
  'SERVICES',
  'GLOBAL',
  'RESEARCH',
  'NOTE',
  'WEEK',
  'CONTINUES',
  'EARNINGS',
  'PRESSURE',
  'DEMAND',
  'MACRO',
  'KEY',
  'TAKEAWAYS',
  'AMP',
  'HIS',
  'IMPLICATIONS',
  'IPO',
  'USD',
  'INR',
  'CEO',
  'GDP',
  'RBI',
  'AGI',
  'CMS',
  'QOQ',
  'YOY',
  'AI',
  'IT',
]);

export function extractTickersFromText(...parts) {
  const text = parts.filter(Boolean).join(' ').toUpperCase();
  const matches = text.match(/\b[A-Z]{2,12}\b/g) || [];
  return [
    ...new Set(
      matches.filter(
        (t) =>
          !TICKER_BLOCK.has(t) &&
          (KNOWN_TICKERS.has(t) || t.endsWith('BANK'))
      )
    ),
  ].slice(0, 12);
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function isTransientTransportError(err, status) {
  if ([502, 503, 504].includes(Number(status))) return true;
  const msg = String(err?.message || err || '');
  const name = String(err?.name || '');
  return (
    name === 'TypeError' ||
    name === 'AbortError' ||
    name === 'TimeoutError' ||
    /failed to fetch|fetch failed|networkerror|network request failed|load failed|timed out|timeout|aborted|502|503|504|unavailable|econnreset|enotfound/i.test(
      msg
    )
  );
}

async function warmNode(base) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 20_000);
  try {
    await fetch(`${base}/api/health`, {
      method: 'GET',
      credentials: 'include',
      signal: ctrl.signal,
    }).catch(() => null);
  } finally {
    clearTimeout(timer);
  }
}

async function postJson(url, body, { timeoutMs = 30_000 } = {}) {
  const resp = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await resp.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  return { resp, data };
}

async function getJson(url, { timeoutMs = 20_000 } = {}) {
  const resp = await fetch(url, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(timeoutMs),
  });
  const text = await resp.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = { raw: text };
  }
  return { resp, data };
}

function phaseLabel(job) {
  const status = job?.status;
  const phase = job?.phase;
  if (status === 'completed') return 'completed';
  if (status === 'failed_permanent' || phase === 'dead_letter') return 'failed_permanent';
  if (status === 'failed') return 'failed';
  if (status === 'waking' || phase === 'waking_engine') return 'waking';
  if (status === 'processing' || phase === 'ingesting') return 'processing';
  if (phase === 'retry_scheduled' || phase === 'reclaimed_after_stall') return 'retry';
  return 'queued';
}

/**
 * Push CMS research into intelligence via async job queue.
 * POST returns 202 + job_id immediately; client polls until completed/failed.
 */
export async function ingestArticleToIntelligence({
  title,
  contentHtml,
  slug,
  articleId,
  section,
  tags = [],
  status,
  destination = 'intelligence',
  onAttempt,
  pollMs = 2_000,
  maxWaitMs = 180_000,
}) {
  const content = stripHtml(contentHtml);
  if (!title?.trim() || content.length < 40) {
    throw new Error('Add a title and enough article content before sending to intelligence.');
  }

  const tickers = extractTickersFromText(title, ...(tags || []), content.slice(0, 1200));
  const base = (API_ORIGIN || '').replace(/\/$/, '');
  if (!base) {
    throw new Error('API origin missing. Set VITE_API_URL for the Hostinger build.');
  }

  const payload = {
    title: title.trim(),
    content,
    slug,
    article_id: articleId || slug,
    section,
    tickers,
    themes: Array.isArray(tags) ? tags.slice(0, 8) : [],
    cms_status: status,
    destination,
    document_type: destination === 'website' ? 'agi_research' : 'agi_note',
    author: 'AGI Research Desk',
  };

  if (typeof onAttempt === 'function') {
    onAttempt({ phase: 'enqueue', attempt: 0, maxAttempts: 1, label: 'Creating ingest job…' });
  }
  await warmNode(base);

  let enqueueData = null;
  let lastError = null;
  for (let attempt = 1; attempt <= 4; attempt += 1) {
    try {
      const { resp, data } = await postJson(`${base}/api/intelligence/kip/ingest/agi`, payload);
      if (resp.status === 202 || resp.ok || data?.job_id || data?.id) {
        enqueueData = data;
        break;
      }
      const detail =
        data?.detail || data?.error || data?.hint || `Failed to queue ingest (${resp.status})`;
      lastError = new Error(String(detail));
      if (!isTransientTransportError(lastError, resp.status) || attempt === 4) throw lastError;
      await warmNode(base);
      await sleep(1500 * attempt);
    } catch (err) {
      lastError = err instanceof Error ? err : new Error(String(err));
      if (!isTransientTransportError(lastError) || attempt === 4) throw lastError;
      await warmNode(base);
      await sleep(1500 * attempt);
    }
  }

  if (!enqueueData) throw lastError || new Error('Failed to queue intelligence ingest.');

  const jobId = enqueueData.job_id || enqueueData.id;
  if (!jobId) {
    // Legacy/partial response — treat queued as soft success.
    return {
      ...enqueueData,
      queued: true,
      pending: true,
    };
  }

  if (typeof onAttempt === 'function') {
    onAttempt({
      phase: phaseLabel(enqueueData),
      attempt: enqueueData.attempt || 1,
      maxAttempts: enqueueData.max_attempts || 6,
      jobId,
      label: enqueueData.already_queued
        ? 'Already queued — waiting for worker…'
        : 'Job queued — worker starting…',
    });
  }

  const started = Date.now();
  let lastJob = enqueueData;

  while (Date.now() - started < maxWaitMs) {
    await sleep(pollMs);
    try {
      const { resp, data } = await getJson(
        `${base}/api/intelligence/cms/ingest-jobs/${encodeURIComponent(jobId)}`
      );
      if (!resp.ok) {
        if (isTransientTransportError(null, resp.status)) continue;
        throw new Error(data?.error || `Job poll failed (${resp.status})`);
      }
      lastJob = data;
      const labelMap = {
        queued: 'Queued…',
        waking: 'Waking intelligence engine…',
        processing: 'Ingesting into institutional memory…',
        retry: `Retry scheduled (attempt ${data.attempt}/${data.max_attempts})…`,
        completed: 'Completed',
        failed: 'Failed',
        failed_permanent: 'Failed permanently (dead-letter) — edit content and send again',
      };
      const phase = phaseLabel(data);
      if (typeof onAttempt === 'function') {
        onAttempt({
          phase,
          attempt: data.attempt || 0,
          maxAttempts: data.max_attempts || 6,
          jobId,
          label: labelMap[phase] || data.phase || phase,
          job: data,
        });
      }
      if (data.status === 'completed' || (data.terminal && data.completed)) {
        return {
          ...data,
          document_id: data.document_id,
          queued: false,
          pending: false,
          completed: true,
        };
      }
      if (data.status === 'failed' || data.status === 'failed_permanent' || data.failed_permanent) {
        throw new Error(
          data.error ||
            (data.status === 'failed_permanent'
              ? 'Intelligence ingest permanently failed (dead-letter).'
              : 'Intelligence ingest job failed.')
        );
      }
      if (data.terminal) {
        throw new Error(data.error || `Ingest ended in terminal state: ${data.status}`);
      }
    } catch (err) {
      if (isTransientTransportError(err)) continue;
      throw err instanceof Error ? err : new Error(String(err));
    }
  }

  // Timed out waiting — job may still complete in background (not a user-facing hard fail).
  return {
    ...lastJob,
    job_id: jobId,
    queued: true,
    pending: true,
    poll_timeout: true,
    message:
      'Ingest is still running in the background. Your draft is safe — no need to click Send again. Polling stopped after the UI wait budget.',
  };
}
