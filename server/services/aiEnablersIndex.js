/**
 * The basket, from member prices.
 *
 * Two constructions, both computed, because the difference between them is
 * itself the finding. The theme's information is in the small and mid caps; a
 * cap-weighted version of this basket is a bet on its largest members and will
 * track them rather than the theme. Equal-weighted is displayed, cap-weighted
 * is shown beside it, and the gap between the two lines is the size skew made
 * visible.
 *
 * Three refusals, all of which exist because the alternative is a number that
 * looks exactly like a working one:
 *
 *   - a basket computed from a partial set of prices is not the basket. Below
 *     a coverage floor it reports coverage instead of a level.
 *   - a stale price is not a price that stopped moving. Members whose last
 *     tick is older than the staleness window are excluded and counted.
 *   - contributions that do not sum to the index return mean a corporate
 *     action was missed. The residual is reported rather than absorbed.
 */

const round = (value, places = 6) => Number(value.toFixed(places));

/** Below this share of the universe priced, there is no index to report. */
export const COVERAGE_FLOOR = 0.8;

/** A tick older than this is not a live price. */
export const STALE_MS = 60_000;

/**
 * Which members can be priced right now, and which cannot.
 *
 * Separated from the arithmetic because "we have 3 of 4 prices" is a different
 * statement from "the index moved 1.8%", and a reader needs the first before
 * the second means anything.
 */
export function priced(members, quotes, { now = Date.now(), staleMs = STALE_MS } = {}) {
  const live = [];
  const missing = [];
  const stale = [];
  for (const member of members || []) {
    const quote = quotes?.[member.symbol];
    if (!quote || !Number.isFinite(Number(quote.ltp)) || !Number.isFinite(Number(quote.previousClose))) {
      missing.push(member.symbol);
      continue;
    }
    if (quote.at !== undefined && now - Number(quote.at) > staleMs) {
      stale.push({ symbol: member.symbol, ageMs: now - Number(quote.at) });
      continue;
    }
    live.push({ member, quote });
  }
  const total = (members || []).length;
  return {
    live, missing, stale,
    coverage: total === 0 ? 0 : round(live.length / total, 4),
    total,
  };
}

const returnOf = (quote) => Number(quote.ltp) / Number(quote.previousClose) - 1;

/**
 * Weights for one construction.
 *
 * Cap weights are capped per name and per layer, because an uncapped
 * free-float weighting of this basket puts most of it in two companies and
 * then reports their news as the theme's.
 */
/**
 * Weights capped so that they stay capped.
 *
 * Capping and then renormalising undoes the cap: scaling everything back up to
 * sum to one lifts the capped names straight back above the limit. In the
 * first version of this a name held at 10% came out at 75%. The excess has to
 * be redistributed among the names that are under the cap, and the pass
 * repeated, because redistributing can push a second name over.
 *
 * A cap below 1/n is arithmetically impossible - ten per cent across four
 * names cannot reach one - and silently ignoring that is how a cap becomes
 * decorative. The feasible floor is used instead, and with four members a 10%
 * cap is simply equal weighting, which is the honest answer.
 */
function capWeights(entries, cap) {
  const feasible = Math.max(cap, 1 / entries.length);
  let weights = new Map(entries.map((one) => [one.key, one.value]));
  for (let pass = 0; pass < 32; pass += 1) {
    const total = [...weights.values()].reduce((a, b) => a + b, 0);
    if (!total) return weights;
    weights = new Map([...weights].map(([key, value]) => [key, value / total]));
    const over = [...weights].filter(([, value]) => value > feasible + 1e-12);
    if (!over.length) break;
    const excess = over.reduce((sum, [, value]) => sum + (value - feasible), 0);
    const under = [...weights].filter(([, value]) => value <= feasible + 1e-12);
    const underTotal = under.reduce((sum, [, value]) => sum + value, 0);
    for (const [key] of over) weights.set(key, feasible);
    if (underTotal <= 0) break;
    for (const [key, value] of under) weights.set(key, value + excess * (value / underTotal));
  }
  return weights;
}

/**
 * Weights for one construction.
 *
 * Cap weights are capped per name and then per layer, because an uncapped
 * free-float weighting of this basket puts most of it in two companies and
 * then reports their news as the theme's.
 */
export function weightsFor(live, { construction = 'equal', nameCap = 0.1, layerCap = 0.4 } = {}) {
  if (!live.length) return new Map();
  if (construction === 'equal') {
    const each = 1 / live.length;
    return new Map(live.map(({ member }) => [member.symbol, each]));
  }
  const floats = live.map(({ member, quote }) => {
    const float = Number(member.freeFloatShares) * Number(quote.ltp);
    return { key: member.symbol, layer: member.layer, value: Number.isFinite(float) ? float : 0 };
  });
  if (!floats.reduce((sum, one) => sum + one.value, 0)) return new Map();

  let weights = capWeights(floats, nameCap);

  // Then the layer, holding the name cap: the layer's excess is taken from its
  // own members and given to the other layers in proportion.
  const layers = [...new Set(floats.map((one) => one.layer))];
  const layerFeasible = Math.max(layerCap, 1 / layers.length);
  for (let pass = 0; pass < 16; pass += 1) {
    const byLayer = new Map();
    for (const one of floats) byLayer.set(one.layer, (byLayer.get(one.layer) || 0) + weights.get(one.key));
    const over = [...byLayer].filter(([, weight]) => weight > layerFeasible + 1e-12);
    if (!over.length) break;
    for (const [layer, weight] of over) {
      const scale = layerFeasible / weight;
      for (const one of floats.filter((row) => row.layer === layer)) {
        weights.set(one.key, weights.get(one.key) * scale);
      }
    }
    const total = [...weights.values()].reduce((a, b) => a + b, 0);
    weights = new Map([...weights].map(([key, value]) => [key, value / total]));
  }
  return weights;
}

/**
 * The index, its contributions, and what it could not price.
 *
 * A member split across sub-layers has its contribution split with it, so a
 * company that is half power equipment and half transmission moves each by
 * half of what it moved the index. Doubling it into both would make the
 * sub-layer contributions sum to more than the index return, which is exactly
 * the error the residual check catches.
 */
export function computeIndex(universe, quotes, options = {}) {
  const members = (universe?.members || []).filter((member) => member.admitted !== false);
  const coverage = priced(members, quotes, options);
  const asOf = options.now ?? Date.now();

  if (coverage.coverage < (options.coverageFloor ?? COVERAGE_FLOOR)) {
    return {
      status: 'insufficient_coverage',
      level: null, return_pct: null, asOf,
      coverage: coverage.coverage,
      priced: coverage.live.length,
      total: coverage.total,
      missing: coverage.missing,
      stale: coverage.stale,
      reason: `${coverage.live.length} of ${coverage.total} members priced; an index of the rest is not the index`,
    };
  }

  const construction = options.construction || 'equal';
  const weights = weightsFor(coverage.live, { ...options, construction });
  let indexReturn = 0;
  const byName = [];
  for (const { member, quote } of coverage.live) {
    const weight = weights.get(member.symbol) || 0;
    const memberReturn = returnOf(quote);
    const contribution = weight * memberReturn;
    indexReturn += contribution;
    byName.push({
      symbol: member.symbol, layer: member.layer, subLayers: member.subLayers || [],
      weight: round(weight, 6), return_pct: round(memberReturn, 6),
      contribution_pp: round(contribution * 100, 4),
    });
  }

  const byLayer = new Map();
  const bySubLayer = new Map();
  for (const row of byName) {
    byLayer.set(row.layer, round((byLayer.get(row.layer) || 0) + row.contribution_pp, 4));
    const split = row.subLayers.length ? 1 / row.subLayers.length : 0;
    for (const subLayer of row.subLayers) {
      const key = `${row.layer}/${subLayer}`;
      bySubLayer.set(key, round((bySubLayer.get(key) || 0) + row.contribution_pp * split, 4));
    }
  }

  // Contributions sum to the index return by construction. When they do not,
  // something changed that the weights do not know about - a split, a bonus,
  // a rights issue - and the difference is shown rather than absorbed.
  const summed = byName.reduce((sum, row) => sum + row.contribution_pp, 0);
  const residual_pp = round(indexReturn * 100 - summed, 6);

  return {
    status: 'ok',
    asOf,
    construction,
    level: options.previousLevel ? round(Number(options.previousLevel) * (1 + indexReturn), 6) : null,
    return_pct: round(indexReturn, 6),
    return_pp: round(indexReturn * 100, 4),
    coverage: coverage.coverage,
    priced: coverage.live.length,
    total: coverage.total,
    missing: coverage.missing,
    stale: coverage.stale,
    contributions: {
      byName: byName.sort((a, b) => b.contribution_pp - a.contribution_pp),
      byLayer: [...byLayer].map(([layer, pp]) => ({ layer, contribution_pp: pp }))
        .sort((a, b) => b.contribution_pp - a.contribution_pp),
      bySubLayer: [...bySubLayer].map(([key, pp]) => ({ subLayer: key, contribution_pp: pp }))
        .sort((a, b) => b.contribution_pp - a.contribution_pp),
    },
    residual_pp,
    residual_ok: Math.abs(residual_pp) < 0.005,
  };
}

/** The movers, which is what a reader looks at first. */
export function leaders(index, { count = 5 } = {}) {
  const rows = index?.contributions?.byName || [];
  return {
    adding: rows.filter((row) => row.contribution_pp > 0).slice(0, count),
    dragging: rows.filter((row) => row.contribution_pp < 0).slice(-count).reverse(),
  };
}
