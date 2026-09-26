/**
 * AGI estimates: scenario arithmetic on disclosed figures.
 *
 * Everything else on the India AI page is what companies disclose. This
 * module is the one place that estimates, and it is built so the line between
 * the two stays visible:
 *
 * - every input is either `disclosed` (a figure with its document) or an
 *   `assumption` (a value with its low/high range and the reason for it);
 * - a model never runs on a missing input. Where AGI has no defensible
 *   anchor (a data-centre share a company has never stated), the input is
 *   null until the reader sets it, and the model says what it is waiting for;
 * - materiality is measured against the company's filed FY26 EBITDA, so no
 *   estimate of total future earnings is needed to express it.
 *
 * No broker estimate is used anywhere: implied growth runs on AGI's own
 * market value and each company's filed profit.
 */

/** A parameter's value under a scenario ('low' | 'base' | 'high'), or an override. */
export function valueOf(param, scenario = 'base', overrides = {}, key = null) {
  if (key && overrides[key] !== undefined && overrides[key] !== null && overrides[key] !== '') {
    const v = Number(overrides[key]);
    return Number.isFinite(v) ? v : null;
  }
  if (!param) return null;
  if (param.kind === 'disclosed') return Number.isFinite(param.value) ? param.value : null;
  const v = scenario === 'low' ? param.low : scenario === 'high' ? param.high : param.value;
  return Number.isFinite(v) ? v : null;
}

const round = (v, d = 1) => (Number.isFinite(v) ? Number(v.toFixed(d)) : null);

/**
 * Run one company's model.
 *
 * `model.params` maps names to parameters; the formula depends on `type`.
 * Returns { ok, missing, aiRevenueCr, aiEbitdaCr, materiality, steps } where
 * steps are the arithmetic in words, so the page can show its working.
 */
export function runModel(model, { scenario = 'base', overrides = {} } = {}) {
  const p = model.params || {};
  const get = (name) => valueOf(p[name], scenario, overrides, `${model.symbol}.${name}`);
  const need = (names) => names.filter((n) => get(n) === null);
  const years = get('years');
  let aiRevenueCr = null;
  const steps = [];
  let missing = [];

  switch (model.type) {
    case 'growBase': {
      // Disclosed AI/DC revenue base (or total revenue x a share), grown.
      missing = need(['years', 'growth', 'margin']);
      let base = get('aiRevenueBaseCr');
      if (base === null) {
        const rev = get('revenueBaseCr');
        const share = get('dcShare');
        if (rev === null) missing.push('revenueBaseCr');
        if (share === null) missing.push('dcShare');
        if (rev !== null && share !== null) {
          base = rev * share;
          steps.push(`data-centre revenue base = ${round(rev, 0)} x ${round(share * 100)}% = ${round(base, 0)} cr`);
        }
      } else {
        steps.push(`AI/data-centre revenue base = ${round(base, 0)} cr`);
      }
      if (missing.length || base === null) break;
      aiRevenueCr = base * (1 + get('growth')) ** years;
      steps.push(`grown ${round(get('growth') * 100)}% a year for ${years} years = ${round(aiRevenueCr, 0)} cr`);
      break;
    }
    case 'contract': {
      // A disclosed contract value recognised evenly over its stated period.
      missing = need(['contractValueCr', 'years', 'margin']);
      if (missing.length) break;
      aiRevenueCr = get('contractValueCr') / years;
      steps.push(`${round(get('contractValueCr'), 0)} cr over ${years} years = ${round(aiRevenueCr, 0)} cr a year`);
      if (get('otherAiRevenueCr') !== null) {
        aiRevenueCr += get('otherAiRevenueCr');
        steps.push(`plus other AI/data-centre revenue ${round(get('otherAiRevenueCr'), 0)} cr = ${round(aiRevenueCr, 0)} cr`);
      }
      break;
    }
    case 'target': {
      // A management revenue target, discounted by an assumed achievement.
      missing = need(['targetRevenueCr', 'achievement', 'margin']);
      if (missing.length) break;
      aiRevenueCr = get('targetRevenueCr') * get('achievement');
      steps.push(`management target ${round(get('targetRevenueCr'), 0)} cr x ${round(get('achievement') * 100)}% achieved = ${round(aiRevenueCr, 0)} cr`);
      break;
    }
    case 'capacity': {
      // Megawatts in operation at the horizon x revenue per MW.
      missing = need(['operatingMW', 'addedMW', 'utilisation', 'revenuePerMWCr', 'margin']);
      if (missing.length) break;
      const mw = get('operatingMW') + get('addedMW');
      aiRevenueCr = mw * get('utilisation') * get('revenuePerMWCr');
      steps.push(`${round(get('operatingMW'), 1)} MW today + ${round(get('addedMW'), 0)} MW added = ${round(mw, 0)} MW`);
      steps.push(`x ${round(get('utilisation') * 100)}% utilised x ${round(get('revenuePerMWCr'), 2)} cr per MW a year = ${round(aiRevenueCr, 0)} cr`);
      break;
    }
    case 'marketShare': {
      // Industry demand a year (MW x content per MW) x the company's share.
      missing = need(['mwPerYear', 'contentPerMWCr', 'share', 'margin']);
      if (missing.length) break;
      const pool = get('mwPerYear') * get('contentPerMWCr');
      aiRevenueCr = pool * get('share');
      steps.push(`${round(get('mwPerYear'), 0)} MW a year x ${get('contentPerMWCr')} cr per MW = ${round(pool, 0)} cr of industry demand`);
      steps.push(`x ${round(get('share') * 100)}% share = ${round(aiRevenueCr, 0)} cr`);
      break;
    }
    case 'osat': {
      // Packaging capacity (units a day) x utilisation x price per package.
      // Neither utilisation nor price is disclosed by the companies modelled,
      // so these default to null and the model waits for the reader.
      missing = need(['unitsPerDay', 'utilisation', 'pricePerUnitRs', 'margin']);
      if (missing.length) break;
      const units = get('unitsPerDay') * 365 * get('utilisation');
      aiRevenueCr = (units * get('pricePerUnitRs')) / 1e7;
      steps.push(`${round(get('unitsPerDay') / 1e6, 2)} m units a day x 365 x ${round(get('utilisation') * 100)}% utilised = ${round(units / 1e9, 2)} bn units a year`);
      steps.push(`x Rs ${get('pricePerUnitRs')} a unit = ${round(aiRevenueCr, 0)} cr`);
      break;
    }
    default:
      return { ok: false, missing: ['a known model type'], steps: [] };
  }

  if (missing.length || aiRevenueCr === null) {
    return { ok: false, missing: [...new Set(missing)], steps };
  }
  // A joint venture counts at the company's share of it.
  const own = get('ownershipShare');
  if (own !== null && own !== 1) {
    aiRevenueCr *= own;
    steps.push(`x ${round(own * 100)}% ownership = ${round(aiRevenueCr, 0)} cr attributable`);
  }
  const margin = get('margin');
  const aiEbitdaCr = aiRevenueCr * margin;
  steps.push(`x ${round(margin * 100)}% EBITDA margin = ${round(aiEbitdaCr, 0)} cr EBITDA`);
  const totalEbitda = get('totalEbitdaFY26Cr');
  const materiality = totalEbitda ? aiEbitdaCr / totalEbitda : null;
  if (materiality !== null) steps.push(`= ${round(materiality * 100)}% of FY26 filed EBITDA (${round(totalEbitda, 0)} cr)`);
  return {
    ok: true, missing: [],
    aiRevenueCr: round(aiRevenueCr, 0), aiEbitdaCr: round(aiEbitdaCr, 0),
    materiality: materiality === null ? null : round(materiality, 4), steps,
  };
}

/**
 * The profit growth today's market value implies.
 *
 * If the market value is to equal `exitMultiple` x profit after `years`,
 * profit must compound from the filed figure at this rate. A statement about
 * what the price assumes, under the reader's chosen exit multiple, not a
 * forecast of either.
 */
export function impliedGrowth({ marketValueCr, patCr, exitMultiple, years }) {
  if (![marketValueCr, patCr, exitMultiple, years].every((v) => Number.isFinite(v) && v > 0)) return null;
  const requiredPat = marketValueCr / exitMultiple;
  return {
    trailingMultiple: round(marketValueCr / patCr, 1),
    requiredPatCr: round(requiredPat, 0),
    cagr: round((requiredPat / patCr) ** (1 / years) - 1, 4),
  };
}

/**
 * A data centre's annual electricity, from its IT load.
 *
 * facility load = IT MW x PUE; energy = facility MW x 8,760 hours. PUE (power
 * usage effectiveness) is an assumption the reader sets; nothing here is a
 * company figure. Returns GWh a year.
 */
export function dcElectricityGWh({ itMW, pue }) {
  if (!(Number.isFinite(itMW) && itMW > 0 && Number.isFinite(pue) && pue >= 1)) return null;
  return round(itMW * pue * 8760 / 1000, 2);
}

/**
 * The equipment a data-centre build-out buys, by layer.
 *
 * MW added x Rs crore of content per MW, for each layer. An industry total,
 * split so layers are not double counted; it assigns nothing to any company.
 * Layers with no per-MW figure are reported as missing, not zero.
 */
export function marketSize({ addedMW, layers = [] }) {
  if (!(Number.isFinite(addedMW) && addedMW > 0)) return null;
  const rows = layers.map((layer) => {
    const low = Number.isFinite(layer.lowCrPerMW) ? layer.lowCrPerMW : null;
    const high = Number.isFinite(layer.highCrPerMW) ? layer.highCrPerMW : low;
    return {
      key: layer.key,
      label: layer.label,
      lowCr: low === null ? null : round(addedMW * low, 0),
      highCr: high === null ? null : round(addedMW * high, 0),
    };
  });
  const priced = rows.filter((r) => r.lowCr !== null);
  return {
    rows,
    totalLowCr: round(priced.reduce((s, r) => s + r.lowCr, 0), 0),
    totalHighCr: round(priced.reduce((s, r) => s + r.highCr, 0), 0),
    unpriced: rows.filter((r) => r.lowCr === null).map((r) => r.label),
  };
}
