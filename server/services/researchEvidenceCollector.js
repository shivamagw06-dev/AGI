import { mergeResearchEvidence, normalizeCatalystEvidence, normalizeHedgeFundEvidence, normalizeValuationEvidence } from './researchEvidenceAdapters.js';

let cache = { at: 0, evidence: [], health: null };
const CACHE_MS = 5 * 60_000;
const ENGINE_GET_TIMEOUT_MS = 8_000;

function engineConfig() {
  let baseUrl = String(process.env.INTELLIGENCE_ENGINE_URL || 'http://127.0.0.1:8100').trim().replace(/\/$/, '');
  if (baseUrl && !/^https?:\/\//i.test(baseUrl)) baseUrl = `https://${baseUrl}`;
  return { baseUrl, token: String(process.env.INTELLIGENCE_ENGINE_TOKEN || 'dev-intelligence-token').trim() };
}

function isTimeout(error) {
  const name = error?.name || '';
  return name === 'TimeoutError' || name === 'AbortError' || /timed out|aborted/i.test(String(error?.message || ''));
}

async function engineGet(path, fetchImpl) {
  const { baseUrl, token } = engineConfig();
  let response;
  try {
    response = await fetchImpl(`${baseUrl}${path}`, {
      headers: { Accept: 'application/json', Authorization: `Bearer ${token}`, 'X-AGI-Intelligence-Token': token },
      signal: AbortSignal.timeout(ENGINE_GET_TIMEOUT_MS),
    });
  } catch (error) {
    if (isTimeout(error)) {
      const timeoutError = new Error('Evidence is not available yet.');
      timeoutError.code = 'EVIDENCE_NOT_AVAILABLE';
      timeoutError.status = 408;
      throw timeoutError;
    }
    throw error;
  }
  if (response.status === 404) {
    const error = new Error('Evidence is not available yet.');
    error.code = 'EVIDENCE_NOT_AVAILABLE'; error.status = 404;
    throw error;
  }
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
  const errors = [], unavailable = [];
  try {
    const terminal = await engineGet('/v1/hedge-fund-lab/terminal', fetchImpl);
    hedgeFund = normalizeHedgeFundEvidence(terminal?.payload || terminal);
  } catch (error) {
    if (error.code === 'EVIDENCE_NOT_AVAILABLE') {
      unavailable.push({ source: 'hedge_fund_lab', reason: 'NO_TERMINAL_SNAPSHOT_YET' });
    } else {
      errors.push({ source: 'hedge_fund_lab', error: error.message });
    }
  }
  const requested = [
    ...(workspace?.groww?.equities || []).map((row) => row.symbol),
    ...(workspace?.signals || []).map((row) => row.symbol),
    ...hedgeFund.map((row) => row.symbol),
  ].map((symbol) => String(symbol || '').toUpperCase()).filter(Boolean);
  const symbols = [...new Set(requested)].slice(0, Math.max(1, Math.min(12, limit)));
  const enriched = await mapLimit(symbols, 1, async (symbol) => {
    const [valuation, catalysts] = await Promise.allSettled([
      engineGet(`/v1/valuation-terminal/company/${encodeURIComponent(symbol)}?window=5Y`, fetchImpl),
      engineGet(`/v1/forecast/catalysts/${encodeURIComponent(symbol)}`, fetchImpl),
    ]);
    if (valuation.status === 'rejected' && valuation.reason.code !== 'EVIDENCE_NOT_AVAILABLE') errors.push({ source: 'valuation_terminal', symbol, error: valuation.reason.message });
    if (catalysts.status === 'rejected' && catalysts.reason.code !== 'EVIDENCE_NOT_AVAILABLE') errors.push({ source: 'forecast_intelligence', symbol, error: catalysts.reason.message });
    if (valuation.status === 'rejected' && valuation.reason.code === 'EVIDENCE_NOT_AVAILABLE') unavailable.push({ source: 'valuation_terminal', symbol, reason: 'NO_VALUATION_PACK_YET' });
    if (catalysts.status === 'rejected' && catalysts.reason.code === 'EVIDENCE_NOT_AVAILABLE') unavailable.push({ source: 'forecast_intelligence', symbol, reason: 'NO_ELIGIBLE_FORECAST_YET' });
    const valuationPack = valuation.status === 'fulfilled' ? valuation.value : null;
    if (valuationPack && valuationPack.ok === false && valuationPack.error === 'NO_VALUATION_PACK_YET') {
      unavailable.push({ source: 'valuation_terminal', symbol, reason: 'NO_VALUATION_PACK_YET' });
    }
    return mergeResearchEvidence(
      valuation.status === 'fulfilled' && valuationPack?.ok !== false ? [normalizeValuationEvidence(symbol, valuationPack)] : [],
      catalysts.status === 'fulfilled' ? [normalizeCatalystEvidence(symbol, catalysts.value, { now })] : [],
      catalysts.status === 'rejected' && catalysts.reason.code === 'EVIDENCE_NOT_AVAILABLE' ? [{ symbol, catalyst_score: null, provenance: { catalyst: { engine: 'forecast_intelligence', forecast_available: false, reason: 'NO_ELIGIBLE_FORECAST_YET' } } }] : [],
    );
  });
  return {
    evidence: mergeResearchEvidence(hedgeFund, ...enriched),
    health: { generated_at: now.toISOString(), candidates: symbols.length, populated: { fundamental: hedgeFund.filter((row) => row.fundamental_score != null).length, valuation: enriched.flat().filter((row) => row.valuation_score != null).length, catalyst: enriched.flat().filter((row) => row.catalyst_score != null).length }, unavailable: unavailable.slice(0, 50), errors: errors.slice(0, 20) },
  };
}

export async function getResearchEvidence(options = {}) {
  if (!options.force && Date.now() - cache.at < CACHE_MS) return { evidence: cache.evidence, health: { ...cache.health, cache: 'hit' } };
  const result = await collectResearchEvidence(options);
  cache = { at: Date.now(), ...result };
  return { ...result, health: { ...result.health, cache: 'miss' } };
}

export function resetResearchEvidenceCache() { cache = { at: 0, evidence: [], health: null }; }
