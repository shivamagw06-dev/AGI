/**
 * Upstox API health — probes corporate-actions for a known ISIN.
 * Never returns secrets; returns a short public-data sample on success.
 */

import {
  FUNDAMENTAL_ENDPOINTS,
  getCompetitors,
  getCorporateActions,
  getFundamentals,
  getHistoricalCandles,
  isUpstoxConfigured,
  resolveUpstoxAccessToken,
  upstoxEnvPresence,
} from '../providers/upstox.js';

const DEFAULT_ISIN = 'INE002A01018'; // Reliance Industries

function detailMap(event) {
  const out = {};
  for (const row of event?.event_details || []) {
    if (row?.name) out[String(row.name)] = row.value ?? null;
  }
  return out;
}

function sanitizeEvents(payload, limit = 5) {
  const rows = Array.isArray(payload?.data) ? payload.data : [];
  return {
    status: payload?.status || null,
    count: rows.length,
    sample: rows.slice(0, limit).map((ev) => {
      const details = detailMap(ev);
      return {
        name: ev?.name ?? null,
        expiry_date: ev?.expiry_date ?? null,
        amount: ev?.amount ?? null,
        ratio: ev?.ratio ?? null,
        announcement_date: details['Announcement date'] ?? null,
        ex_date: details['Ex dividend date'] || details['Ex-date'] || details['Ex date'] || null,
        record_date: details['Record date'] ?? null,
        details: details.Details || details.details || null,
      };
    }),
  };
}

/**
 * How many reporting periods a statement payload carries, and their labels.
 * Period labels (e.g. "FY2024") are metadata, not financial values — knowing
 * the depth is what tells us whether Upstox can stand in for CapIQ history.
 */
function depthOf(data) {
  const periodKeys = new Set();
  let deepest = 0;

  const walk = (node, hops) => {
    if (hops > 4 || !node) return;
    if (Array.isArray(node)) {
      for (const item of node.slice(0, 30)) walk(item, hops + 1);
      return;
    }
    if (typeof node !== 'object') return;
    // A statement line item keyed by period looks like { FY2024: 123, FY2023: 98 }
    const keys = Object.keys(node);
    const periodish = keys.filter((k) => /^(FY|Q[1-4])?\s?-?\d{2,4}/i.test(k) || /\d{4}/.test(k));
    if (periodish.length >= 2 && periodish.length === keys.length) {
      periodish.forEach((k) => periodKeys.add(k));
      deepest = Math.max(deepest, periodish.length);
      return;
    }
    for (const value of Object.values(node).slice(0, 30)) walk(value, hops + 1);
  };

  walk(data, 0);
  const labels = [...periodKeys].sort();
  return {
    periods: deepest,
    period_labels: labels.slice(0, 16),
  };
}

function shapeOf(payload) {
  const data = payload?.data;
  if (Array.isArray(data)) {
    const first = data[0];
    return {
      kind: 'array',
      rows: data.length,
      fields: first && typeof first === 'object' ? Object.keys(first).slice(0, 12) : [],
      ...depthOf(data),
    };
  }
  if (data && typeof data === 'object') {
    return {
      kind: 'object',
      fields: Object.keys(data).slice(0, 15),
      time_period: data.time_period ?? null,
      units_in: data.units_in ?? null,
      ...depthOf(data),
    };
  }
  return { kind: typeof data, rows: 0, fields: [] };
}

/**
 * Probe every fundamentals endpoint plus public candles for one ISIN.
 * Reports availability and payload shape only — never raw statements or secrets.
 */
export async function getUpstoxCapabilities(opts = {}) {
  const isin = String(opts.isin || DEFAULT_ISIN).trim().toUpperCase();
  const instrumentKey = opts.instrumentKey || `NSE_EQ|${isin}`;
  const endpoints = {};

  for (const endpoint of FUNDAMENTAL_ENDPOINTS) {
    try {
      const payload = await getFundamentals(isin, endpoint);
      endpoints[endpoint] = {
        ok: payload?.status === 'success',
        status: payload?.status || null,
        ...shapeOf(payload),
      };
    } catch (err) {
      endpoints[endpoint] = { ok: false, error: err?.message || 'failed', httpStatus: err?.status || null };
    }
  }

  try {
    const payload = await getCompetitors(instrumentKey);
    endpoints.competitors = {
      ok: payload?.status === 'success',
      status: payload?.status || null,
      ...shapeOf(payload),
    };
  } catch (err) {
    endpoints.competitors = { ok: false, error: err?.message || 'failed', httpStatus: err?.status || null };
  }

  const candles = {};
  const to = new Date().toISOString().slice(0, 10);
  for (const [label, spec] of Object.entries({
    monthly_16y: { unit: 'months', interval: 1, from: '2010-01-01' },
    weekly_15y: { unit: 'weeks', interval: 1, from: '2011-01-01' },
    daily_5y: { unit: 'days', interval: 1, from: '2020-01-01' },
  })) {
    try {
      const payload = await getHistoricalCandles(instrumentKey, { ...spec, to });
      const rows = payload?.data?.candles || [];
      candles[label] = {
        ok: rows.length > 0,
        count: rows.length,
        oldest: rows.length ? rows[rows.length - 1][0] : null,
        newest: rows.length ? rows[0][0] : null,
        auth_required: false,
      };
    } catch (err) {
      candles[label] = { ok: false, error: err?.message || 'failed' };
    }
  }

  const total = Object.keys(endpoints).length;
  const available = Object.values(endpoints).filter((e) => e.ok).length;
  return {
    provider: 'upstox',
    isin,
    instrument_key: instrumentKey,
    configured: isUpstoxConfigured(),
    fundamentals: endpoints,
    fundamentals_available: `${available}/${total}`,
    candles,
    checkedAt: new Date().toISOString(),
  };
}

export async function getUpstoxHealth(opts = {}) {
  const isin = String(opts.isin || DEFAULT_ISIN).trim().toUpperCase();
  const env = upstoxEnvPresence();
  const resolved = resolveUpstoxAccessToken();
  const configured = isUpstoxConfigured();

  const base = {
    provider: 'upstox',
    configured,
    authSource: resolved.source,
    likelyClientIdOnly: Boolean(resolved.likely_client_id),
    envPresent: env,
    isin,
    checkedAt: new Date().toISOString(),
    docs: 'https://upstox.com/developer/api-documentation/get-corporate-actions/',
  };

  if (!configured) {
    return {
      ...base,
      ok: false,
      message: resolved.likely_client_id
        ? `Env ${resolved.source} looks like client_id — also set UPSTOX_ACCESS_TOKEN (Bearer).`
        : 'Set UPSTOX_ACCESS_TOKEN on Render (finance-news-backend). Optional aliases: UPSTOX_TOKEN, UPSTOX_API (if value is the access token).',
      corporate_actions: null,
    };
  }

  try {
    const raw = await getCorporateActions(isin);
    const corporate_actions = sanitizeEvents(raw);
    return {
      ...base,
      ok: corporate_actions.status === 'success' || corporate_actions.count > 0,
      message:
        corporate_actions.count > 0
          ? `Pulled ${corporate_actions.count} corporate-action event(s) for ${isin}`
          : `Upstox returned success but zero events for ${isin}`,
      corporate_actions,
    };
  } catch (err) {
    return {
      ...base,
      ok: false,
      message: err?.message || 'Upstox corporate-actions failed',
      httpStatus: err?.status || null,
      corporate_actions: null,
    };
  }
}
