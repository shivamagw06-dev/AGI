import { readFile, stat } from 'node:fs/promises';
import { readLatestValuationCompanyPack } from './valuationCompanyPackSnapshot.js';
import { validateRecord } from '../../src/lib/wealthWorkspace.js';
import { date, DAY } from '../../src/lib/wealthPlanning.js';

export async function getWealthEquityResearch(symbol, { readPack = readLatestValuationCompanyPack, now = Date.now } = {}) {
  const pack = await readPack(symbol, { window: '5Y' });
  const generated = pack?.generated_at, age = generated ? now() - Date.parse(generated) : Infinity;
  if (!pack?.ok) return { symbol, status: 'unavailable', metrics: [], reason: 'No stored company research is available. Open company research for the full workflow.' };
  const metrics = (Array.isArray(pack.table) ? pack.table : []).filter(row => row.meaningful && typeof row.company === 'number' && Number.isFinite(row.company)).slice(0, 30)
    .map(row => ({ metric: String(row.metric || ''), value: row.company, position: typeof row.position === 'string' ? row.position : null }));
  return { symbol, name: typeof pack.overview?.name === 'string' ? pack.overview.name : symbol,
    status: age >= 0 && age <= DAY && pack.freshness === 'fresh' ? 'available' : 'stale',
    generatedAt: generated || null, sourceAsOf: typeof pack.source_as_of === 'string' ? pack.source_as_of : null, source: 'AGI stored valuation research', metrics,
    caveat: 'Stored fundamentals are not live quotes. Metric units and reference methodology are available in company research. No automatic suitability or return forecast.' };
}

export function validateEvidenceFeed(raw, now = Date.now()) {
  if (raw?.version !== 'agi-wealth-evidence-v1' || raw.displayRightsConfirmed !== true || typeof raw.provider !== 'string' || !raw.provider.trim()) throw new Error('Provider metadata and display rights are required.');
  if (date(raw.reviewedAt) > now || now - date(raw.reviewedAt) > 90 * DAY) throw new Error('Provider review must be within 90 days.');
  if (!Array.isArray(raw.records) || raw.records.length > 1000) throw new Error('Feed exceeds 1000 records.');
  const ids = new Set();
  const records = raw.records.map(({ kind, ...row }) => {
    if (!['funds','properties','bonds','events'].includes(kind)) throw new Error('Unsupported evidence kind.');
    const record = validateRecord(kind, row, { people:[] }, now);
    const key = `${kind}:${record.id}`; if (ids.has(key)) throw new Error('Duplicate feed identifier.'); ids.add(key);
    const maxAge = kind === 'bonds' ? 7 : kind === 'funds' ? 60 : 180;
    return { kind, record, stale: record.asOf ? now - date(record.asOf) > maxAge * DAY : false };
  });
  return { status:'available', provider:raw.provider.slice(0,200), reviewedAt:raw.reviewedAt, records,
    note:'Provider-supplied evidence; confirm availability, methodology and professional review. Feed review is not title or investment approval.' };
}
/** Configured local feed only: requests cannot choose URLs or filesystem paths. */
export function createEvidenceProvider({ path = () => process.env.WEALTH_EVIDENCE_FILE, read = readFile, info = stat, now = Date.now } = {}) {
  let cached, expires = 0, pending;
  return async () => {
    if (now() < expires && cached) return cached;
    if (pending) return pending;
    pending = (async () => {
      const file = path();
      if (!file) return { status:'not_connected', records:[], note:'No reviewed property, bond or AMC disclosure feed is connected.' };
      try {
        if ((await info(file)).size > 2000000) throw new Error('Too large');
        const body = await read(file, 'utf8'); if (body.length > 2000000) throw new Error('Too large');
        return validateEvidenceFeed(JSON.parse(body), now());
      } catch { return { status:'unavailable', records:[], note:'Configured evidence feed is invalid or unavailable. No records are served.' }; }
    })();
    try { cached = await pending; expires = now() + 60000; return cached; } finally { pending = null; }
  };
}
export const getWealthEvidence = createEvidenceProvider();
