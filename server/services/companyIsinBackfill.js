/**
 * Backfill company_master.isin from Upstox NSE equity instruments (+ optional index CSVs).
 * Required before Upstox key-ratios refresh (fundamentals are ISIN-keyed).
 */

import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import { fileURLToPath } from 'node:url';

const UPSTOX_NSE_INSTRUMENTS =
  'https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz';
const ISIN_RE = /^[A-Z]{2}[A-Z0-9]{9}[0-9]$/;

function engineConfig() {
  let baseUrl = (process.env.AGIB_INTELLIGENCE_ENGINE_URL || process.env.INTELLIGENCE_ENGINE_URL || '').replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  const token = (process.env.AGIB_SERVICE_TOKEN || process.env.INTELLIGENCE_ENGINE_TOKEN || '').trim();
  return { baseUrl, token };
}

async function engineFetch(pathName, { method = 'GET', body = null, timeoutMs = 180_000 } = {}) {
  const { baseUrl, token } = engineConfig();
  if (!baseUrl || !token) {
    return { ok: false, status: 503, data: { error: 'intelligence_engine_not_configured' } };
  }
  const response = await fetch(`${baseUrl}${pathName}`, {
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
    data = { raw: String(text || '').slice(0, 400) };
  }
  return { ok: response.ok, status: response.status, data };
}

function validIsin(value) {
  const text = String(value || '').trim().toUpperCase();
  return ISIN_RE.test(text) ? text : null;
}

export async function loadUpstoxNseIsinMap({ url = UPSTOX_NSE_INSTRUMENTS } = {}) {
  const response = await fetch(url, {
    headers: { Accept: 'application/gzip, application/json', 'User-Agent': 'AGIB-ISIN-Backfill/1.0' },
    signal: AbortSignal.timeout(90_000),
  });
  if (!response.ok) {
    throw new Error(`upstox_instruments_http_${response.status}`);
  }
  const buf = Buffer.from(await response.arrayBuffer());
  const jsonBuf = buf[0] === 0x1f && buf[1] === 0x8b ? zlib.gunzipSync(buf) : buf;
  const data = JSON.parse(jsonBuf.toString('utf8'));
  const out = new Map();
  for (const item of Array.isArray(data) ? data : []) {
    if (!item || item.segment !== 'NSE_EQ') continue;
    if (String(item.instrument_type || '').toUpperCase() !== 'EQ') continue;
    const symbol = String(item.trading_symbol || '').trim().toUpperCase();
    const isin = validIsin(item.isin);
    if (!symbol || !isin) continue;
    out.set(symbol, {
      isin,
      instrument_key: item.instrument_key || `NSE_EQ|${isin}`,
      name: item.name || symbol,
    });
  }
  return out;
}

function loadIndexCsvIsinMap() {
  const out = new Map();
  try {
    const here = path.dirname(fileURLToPath(import.meta.url));
    const root = path.resolve(here, '../../indices');
    if (!fs.existsSync(root)) return out;
    for (const name of fs.readdirSync(root).filter((f) => f.endsWith('.csv'))) {
      const text = fs.readFileSync(path.join(root, name), 'utf8');
      const lines = text.split(/\r?\n/).filter(Boolean);
      if (lines.length < 2) continue;
      const headers = lines[0].split(',').map((h) => h.trim());
      const symIdx = headers.findIndex((h) => /^symbol$/i.test(h));
      const isinIdx = headers.findIndex((h) => /isin/i.test(h));
      if (symIdx < 0 || isinIdx < 0) continue;
      for (const line of lines.slice(1)) {
        const cols = line.split(',');
        const symbol = String(cols[symIdx] || '').trim().toUpperCase();
        const isin = validIsin(cols[isinIdx]);
        if (symbol && isin && !out.has(symbol)) out.set(symbol, isin);
      }
    }
  } catch {
    /* optional */
  }
  return out;
}

/**
 * Prefer engine-native backfill; fall back to Node instruments + warehouse edit.
 */
export async function backfillCompanyIsins({ dryRun = false, forceNode = false } = {}) {
  if (!forceNode) {
    const viaEngine = await engineFetch('/v1/valuation-ratios/isin-backfill', {
      method: 'POST',
      body: { dry_run: !!dryRun, actor: 'company_isin_backfill' },
      timeoutMs: 300_000,
    });
    if (viaEngine.ok && viaEngine.data) {
      return { ok: true, path: 'engine', ...viaEngine.data };
    }
    // Older engines may not have the route yet — fall through to Node path.
    if (viaEngine.status && viaEngine.status !== 404) {
      // keep going; node path still works against warehouse edit
    }
  }

  const [isinMap, csvMap, mastersRes] = await Promise.all([
    loadUpstoxNseIsinMap(),
    Promise.resolve(loadIndexCsvIsinMap()),
    engineFetch('/v1/warehouse/tab/company_master?limit=10000', { timeoutMs: 180_000 }),
  ]);

  const masters = mastersRes.data?.rows || [];
  if (!mastersRes.ok || !Array.isArray(masters)) {
    return {
      ok: false,
      status: mastersRes.status || 502,
      error: 'company_master_unavailable',
      path: 'node',
      detail: mastersRes.data,
    };
  }

  let already = 0;
  let matched = 0;
  let unmatched = 0;
  const edits = [];
  for (const row of masters) {
    const symbol = String(row.symbol || '').trim().toUpperCase();
    if (!symbol) continue;
    if (validIsin(row.isin)) {
      already += 1;
      continue;
    }
    const hit = isinMap.get(symbol);
    const isin = hit?.isin || csvMap.get(symbol) || null;
    if (!isin || !row.row_id) {
      unmatched += 1;
      continue;
    }
    matched += 1;
    edits.push({ row_id: row.row_id, column: 'isin', value: isin });
  }

  if (dryRun || !edits.length) {
    return {
      ok: true,
      path: 'node',
      dry_run: !!dryRun,
      masters: masters.length,
      already_had_isin: already,
      matched,
      unmatched,
      upstox_eq_map: isinMap.size,
      csv_map: csvMap.size,
      would_write: edits.length,
      written: 0,
      sample: edits.slice(0, 10),
    };
  }

  let applied = 0;
  const errors = [];
  for (let i = 0; i < edits.length; i += 200) {
    const chunk = edits.slice(i, i + 200);
    const res = await engineFetch('/v1/warehouse/tab/company_master/edit', {
      method: 'POST',
      body: {
        edits: chunk,
        actor: 'company_isin_backfill',
        reason: 'isin_backfill_upstox_instruments',
        recalculate: false,
      },
      timeoutMs: 180_000,
    });
    if (!res.ok) {
      errors.push({ offset: i, status: res.status, error: res.data?.error || 'edit_failed' });
      continue;
    }
    applied += Number(res.data?.applied ?? chunk.length);
  }

  return {
    ok: errors.length === 0,
    path: 'node',
    dry_run: false,
    masters: masters.length,
    already_had_isin: already,
    matched,
    unmatched,
    upstox_eq_map: isinMap.size,
    csv_map: csvMap.size,
    written: applied,
    errors: errors.slice(0, 5),
    sample: edits.slice(0, 10),
  };
}
