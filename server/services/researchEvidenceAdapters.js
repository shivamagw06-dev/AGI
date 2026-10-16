const FUNDAMENTAL_SCANS = new Set(['alpha', 'quality', 'growth', 'conviction', 'dividend']);

const number = (value) => {
  if (value == null || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};
const clamp = (value) => Math.max(0, Math.min(100, value));
const mean = (values) => {
  const clean = values.map(number).filter((value) => value != null);
  return clean.length ? clean.reduce((sum, value) => sum + value, 0) / clean.length : null;
};
const symbolOf = (row) => String(row?.ticker || row?.symbol || row?.long_leg?.ticker || '').trim().toUpperCase();

export function normalizeHedgeFundEvidence(payload) {
  const bySymbol = new Map();
  for (const card of payload?.cards || []) {
    for (const row of card?.results || []) {
      const symbol = symbolOf(row);
      if (!symbol) continue;
      const evidence = bySymbol.get(symbol) || { symbol, sector: row.sector || row.long_leg?.sector || null, fundamental: [], valuation: [], sources: [] };
      const confidence = number(row.confidence);
      if (confidence != null && FUNDAMENTAL_SCANS.has(card.id)) evidence.fundamental.push(confidence);
      if (confidence != null && card.id === 'value') evidence.valuation.push(confidence);
      evidence.sources.push({ engine: 'hedge_fund_lab', scanner: card.id, confidence, why: row.why || null });
      bySymbol.set(symbol, evidence);
    }
  }
  return [...bySymbol.values()].map((row) => ({
    symbol: row.symbol,
    sector: row.sector,
    fundamental_score: mean(row.fundamental),
    valuation_score: mean(row.valuation),
    observed_at: { fundamental: payload?.as_of || null, valuation: payload?.as_of || null },
    provenance: { fundamental: row.sources.filter((source) => FUNDAMENTAL_SCANS.has(source.scanner)), valuation: row.sources.filter((source) => source.scanner === 'value') },
  }));
}

function firstNumber(source, paths) {
  for (const path of paths) {
    const value = path.split('.').reduce((current, key) => current?.[key], source);
    const parsed = number(value);
    if (parsed != null) return parsed;
  }
  return null;
}

export function normalizeValuationEvidence(symbol, pack) {
  const richness = firstNumber(pack, [
    'derived.relative_valuation.score', 'relative_valuation.score', 'valuation.relative_valuation.score',
    'company.derived.relative_valuation.score', 'historical.percentile', 'valuation.historical_percentile',
  ]);
  const directAttractiveness = firstNumber(pack, ['valuation_attractiveness', 'scores.valuation_attractiveness']);
  const score = directAttractiveness ?? (richness == null ? null : 100 - richness);
  return {
    symbol: String(symbol || '').toUpperCase(),
    valuation_score: score == null ? null : Number(clamp(score).toFixed(2)),
    observed_at: { valuation: pack?.as_of || pack?.generated_at || pack?.valuation_date || null },
    provenance: { valuation: { engine: 'valuation_terminal', richness_percentile: richness, conversion: directAttractiveness == null ? 'attractiveness=100-richness' : 'direct' } },
  };
}

function catalystItems(pack) {
  const candidates = [pack?.catalysts, pack?.items, pack?.timeline, pack?.data?.catalysts];
  for (const value of candidates) {
    if (Array.isArray(value)) return value;
    if (Array.isArray(value?.items)) return value.items;
    if (Array.isArray(value?.timeline)) return value.timeline;
  }
  return [];
}

export function normalizeCatalystEvidence(symbol, pack, { now = new Date() } = {}) {
  const items = catalystItems(pack);
  const scored = items.map((item) => {
    const importance = String(item.importance || item.impact || '').toLowerCase();
    const base = importance === 'high' ? 90 : importance === 'medium' ? 70 : 55;
    const date = Date.parse(item.date || item.event_date || item.as_of || '');
    if (!Number.isFinite(date)) return base * 0.65;
    const days = Math.max(0, (date - now.getTime()) / 86_400_000);
    return base * (2 ** (-days / 30));
  });
  return {
    symbol: String(symbol || '').toUpperCase(),
    catalyst_score: scored.length ? Number(clamp(Math.max(...scored)).toFixed(2)) : null,
    observed_at: { catalyst: pack?.generated_at || pack?.as_of || now.toISOString() },
    catalyst_count: items.length,
    provenance: { catalyst: { engine: 'forecast_intelligence', items: items.slice(0, 5) } },
  };
}

export function mergeResearchEvidence(...collections) {
  const merged = new Map();
  for (const collection of collections) {
    for (const row of collection || []) {
      const symbol = String(row?.symbol || '').toUpperCase();
      if (!symbol) continue;
      const prior = merged.get(symbol) || { symbol, observed_at: {}, provenance: {} };
      merged.set(symbol, { ...prior, ...row, observed_at: { ...prior.observed_at, ...(row.observed_at || {}) }, provenance: { ...prior.provenance, ...(row.provenance || {}) } });
    }
  }
  return [...merged.values()];
}
