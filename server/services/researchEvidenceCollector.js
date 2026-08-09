import { mergeResearchEvidence, normalizeCatalystEvidence, normalizeHedgeFundEvidence, normalizeValuationEvidence } from './researchEvidenceAdapters.js';

let cache = { at: 0, evidence: [], health: null };
const CACHE_MS = 5 * 60_000;

function engineConfig() {
  let baseUrl = String(process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').trim().replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  return { baseUrl, token: String(process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim() };
}

async function engineGet(path, fetchImpl) {
  const { baseUrl, token } = engineConfig();
  const response = await fetchImpl(`${baseUrl}${path}`, { headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, 'X-AGI-Intelligence-Token': token }, signal: AbortSignal.timeout(12_000) });
  if (!response.ok) throw new Error(`Evidence source failed (${response.status}).`);
  return response.json();
}

async function mapLimit(values, concurrency, mapper) {
  const output = new Array(values.length); let cursor = 0;
  await Promise.all(Array.from({ length: Math.min(concurrency, values.length) }, async () => {
    while (cursor < values.length) { const index = cursor; cursor += 1; output[index] = await mapper(values[index], index); }
  }));
  return output;
}

export async function collectResearchEvidence({ workspace, fetchImpl = globalThis.fetch, limit = 12, now = new Date() } = {}) {
  let hedgeFund = [];
  const errors = [];
  try { hedgeFund = normalizeHedgeFundEvidence(await engineGet(`/v1/hedge-fund-lab/terminal?limit=${Math.max(12, limit)}`, fetchImpl)); }
  catch (error) { errors.push({ source: 'hedge_fund_lab', error: error.message }); }
  const requested = [
    ...(workspace?.groww?.equities || []).map((row) => row.symbol),
    ...(workspace?.signals || []).map((row) => row.symbol),
    ...hedgeFund.map((row) => row.symbol),
  ].map((symbol) => String(symbol || '').toUpperCase()).filter(Boolean);
  const symbols = [...new Set(requested)].slice(0, Math.max(1, Math.min(25, limit)));
  const enriched = await mapLimit(symbols, 4, async (symbol) => {
    const [valuation, catalysts] = await Promise.allSettled([
      engineGet(`/v1/valuation-terminal/company/${encodeURIComponent(symbol)}?window=5Y&peer_limit=12`, fetchImpl),
      engineGet(`/v1/forecast/catalysts/${encodeURIComponent(symbol)}`, fetchImpl),
    ]);
    if (valuation.status === 'rejected') errors.push({ source: 'valuation_terminal', symbol, error: valuation.reason.message });
    if (catalysts.status === 'rejected') errors.push({ source: 'forecast_intelligence', symbol, error: catalysts.reason.message });
    return mergeResearchEvidence(
      valuation.status === 'fulfilled' ? [normalizeValuationEvidence(symbol, valuation.value)] : [],
      catalysts.status === 'fulfilled' ? [normalizeCatalystEvidence(symbol, catalysts.value, { now })] : [],
    );
  });
  return {
    evidence: mergeResearchEvidence(hedgeFund, ...enriched),
    health: { generated_at: now.toISOString(), candidates: symbols.length, populated: { fundamental: hedgeFund.filter((row) => row.fundamental_score != null).length, valuation: enriched.flat().filter((row) => row.valuation_score != null).length, catalyst: enriched.flat().filter((row) => row.catalyst_score != null).length }, errors: errors.slice(0, 20) },
  };
}

export async function getResearchEvidence(options = {}) {
  if (!options.force && Date.now() - cache.at < CACHE_MS) return { evidence: cache.evidence, health: { ...cache.health, cache: 'hit' } };
  const result = await collectResearchEvidence(options);
  cache = { at: Date.now(), ...result };
  return { ...result, health: { ...result.health, cache: 'miss' } };
}

export function resetResearchEvidenceCache() { cache = { at: 0, evidence: [], health: null }; }
