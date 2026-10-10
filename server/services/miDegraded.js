/**
 * Degraded Market & Sector Intelligence payload when the engine is unreachable.
 * Keeps the terminal shell usable instead of a hard timeout error.
 */

function nowIso() {
  return new Date().toISOString().replace(/\.\d{3}Z$/, 'Z');
}

export function buildMiDegradedDashboard(detail = 'Intelligence engine unavailable') {
  return {
    ok: false,
    degraded: true,
    engine: 'market-intelligence',
    version: 'mi-v1-degraded',
    constitution: '2.0',
    error: detail,
    hint: 'The intelligence engine may be cold-starting. Retry in a minute or refresh with a warm engine.',
    generated_at: nowIso(),
    overview: { companies: null, valuation_date: null, coverage: { pct: null } },
    market_regime: { regime: 'Unavailable', drivers: [] },
    market_health: { overall: null, market_historical_percentile: null },
    market_drivers: { drivers: [] },
    breadth: { advancing: null, declining: null, unchanged: null, coverage_pct: null },
    flows: { available: false, explanation: 'Engine offline' },
    sectors: [],
    sector_heatmap: [],
    industries: [],
    opportunities: { cards: [] },
    rotation: {},
    research_priorities: [],
    explainability: {},
  };
}

export function buildMiDegradedSector(sector, detail = 'Intelligence engine unavailable') {
  return {
    ok: false,
    degraded: true,
    sector: String(sector || ''),
    error: detail,
    hint: 'Sector workspace unavailable while the engine recovers.',
    companies: [],
    lens: {},
    valuation: {},
    leaders: [],
    laggards: [],
    distribution: {},
    research: {},
    agi_sector_intelligence: null,
  };
}
