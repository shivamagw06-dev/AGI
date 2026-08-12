/**
 * Static Hedge Fund Lab strategy library.
 *
 * Strategy cards / compare / profiles are definitional content — they do not
 * need the Python engine or warehouse. Serving them from Node keeps the HFL
 * page usable when Render returns 502 / circuit-open during engine recovery.
 *
 * Regenerated from intelligence-engine/hedge_fund_lab/strategies.py when the
 * library changes.
 */

import { readFileSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_PATH = join(__dirname, '../data/hflStrategyLibrary.json');

let cache = null;

function load() {
  if (cache) return cache;
  cache = JSON.parse(readFileSync(DATA_PATH, 'utf8'));
  return cache;
}

function intelligenceFor(pack) {
  const works = pack.works_when || [];
  const fails = pack.fails_when || [];
  const institutionalUse = ['long_short_equity', 'equity_market_neutral'].includes(pack.id)
    ? `${pack.name} seeks to reduce dependence on market direction through offsetting long and short exposures, but returns remain sensitive to net beta, factor exposures and short squeezes. Its stated alpha source is ${String(pack.alpha_source || '').toLowerCase()}.`
    : `${pack.name} seeks ${String(pack.alpha_source || '').toLowerCase()} across its stated ${String(pack.holding_period || '').toLowerCase()} holding period. Returns remain exposed to the strategy-specific risks and regimes shown below.`;
  return {
    why_institutions_use_it: institutionalUse,
    when_it_performs: works,
    when_it_struggles: fails,
    favourable_regimes: pack.regimes || [],
    risk_factors: pack.risk_factors || [],
    monitored_kpis: pack.kpis || [],
    common_mistakes: pack.mistakes || [],
    critical_data: pack.key_data || [],
    bottom_line: (
      `The edge is ${String(pack.alpha_source || '').toLowerCase()}, held for `
      + `${pack.holding_period || '—'}. It pays when ${(works[0] || 'conditions align').toLowerCase()}, `
      + `and it breaks when ${(fails[0] || 'the thesis fails').toLowerCase()}.`
    ),
  };
}

export function hflStaticLibrary() {
  const data = load();
  return {
    ok: true,
    strategies: data.strategies || [],
    count: data.count || (data.strategies || []).length,
    source: 'node_static_fallback',
  };
}

export function hflStaticCompare() {
  const data = load();
  return {
    ok: true,
    rows: data.compare_rows || [],
    source: 'node_static_fallback',
  };
}

export function hflStaticStrategy(strategyId) {
  const data = load();
  const id = String(strategyId || '').trim().toLowerCase();
  const pack = (data.profiles || {})[id];
  if (!pack) {
    return { ok: false, error: 'unknown_strategy', strategy_id: strategyId, source: 'node_static_fallback' };
  }
  return { ok: true, ...pack, agi_intelligence: intelligenceFor(pack), source: 'node_static_fallback' };
}
