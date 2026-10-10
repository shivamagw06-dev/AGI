/** Unlevered, nominal, annual scenario model. Rates are user assumptions, not tax advice. */
export const MODEL_VERSION = 'wealth-scenario-v1';

function value(raw, name, min, max) {
  if (!['number','string'].includes(typeof raw) || (typeof raw === 'string' && !raw.trim())) throw new Error(`${name} is required.`);
  const n = Number(raw);
  if (!Number.isFinite(n) || n < min || n > max) throw new Error(`${name} must be between ${min} and ${max}.`);
  return n;
}

export function validatePlan(raw) {
  const plan = {
    capital: value(raw.capital, 'Capital', 1, 1e12),
    years: value(raw.years, 'Holding period', 1, 40),
    fdRate: value(raw.fdRate, 'FD interest rate', 0, 30),
    incomeTax: value(raw.incomeTax, 'Effective income tax rate', 0, 60),
    inflation: value(raw.inflation, 'Inflation', 0, 30),
    reinvest: raw.reinvest === true,
  };
  if (!Number.isInteger(plan.years)) throw new Error('Holding period must be a whole number of years.');
  return plan;
}

export function validateAsset(raw) {
  return {
    ...raw,
    growth: value(raw.growth, 'Annual price growth', -99, 100),
    incomeYield: value(raw.incomeYield, 'Annual cash yield', 0, 40),
    entryCost: value(raw.entryCost, 'Entry costs', 0, 50),
    exitCost: value(raw.exitCost, 'Exit costs', 0, 50),
    annualCost: value(raw.annualCost, 'Annual holding costs', 0, 20),
    gainsTax: value(raw.gainsTax, 'Effective exit gains tax', 0, 60),
  };
}

export function projectAsset(rawPlan, rawAsset) {
  const p = validatePlan(rawPlan);
  const a = validateAsset(rawAsset);
  const initialAsset = p.capital / (1 + a.entryCost / 100);
  const entryCost = p.capital - initialAsset;
  const reinvestRate = p.reinvest ? p.fdRate / 100 * (1 - p.incomeTax / 100) : 0;
  let assetValue = initialAsset, cash = 0, taxPaid = 0, holdingCosts = 0;
  const path = [];
  for (let year = 1; year <= p.years; year += 1) {
    // Holding costs and income are based on the opening asset value.
    const income = assetValue * a.incomeYield / 100;
    const incomeTax = income * p.incomeTax / 100;
    const costs = assetValue * a.annualCost / 100;
    const cashInterestTax = p.reinvest && cash > 0 ? cash * p.fdRate / 100 * p.incomeTax / 100 : 0;
    cash = cash * (cash > 0 ? 1 + reinvestRate : 1) + income - incomeTax - costs;
    assetValue *= 1 + a.growth / 100;
    taxPaid += incomeTax + cashInterestTax;
    holdingCosts += costs;
    const saleCost = assetValue * a.exitCost / 100;
    // Explicit simplification: all entry costs added to basis; no exemptions, indexation or loss credits.
    const exitTax = Math.max(0, assetValue - saleCost - p.capital) * a.gainsTax / 100;
    path.push({ year, assetValue, cash, exitTax, saleCost, netWealth: assetValue - saleCost - exitTax + cash });
  }
  const last = path.at(-1);
  const netWealth = last.netWealth;
  return {
    id: a.id, label: a.label, initialAsset, entryCost, netWealth,
    realWealth: netWealth / (1 + p.inflation / 100) ** p.years,
    annualized: netWealth > 0 ? ((netWealth / p.capital) ** (1 / p.years) - 1) * 100 : null,
    firstYearNetIncome: initialAsset * (a.incomeYield / 100 * (1 - p.incomeTax / 100) - a.annualCost / 100),
    totalTax: taxPaid + last.exitTax,
    totalCosts: entryCost + holdingCosts + last.saleCost,
    exitTax: last.exitTax, cashShortfall: Math.max(0, -Math.min(0, ...path.map(row => row.cash))), path,
  };
}

export function fdAsset(plan) {
  return { id: 'fd', label: 'FD benchmark', growth: 0, incomeYield: plan.fdRate, entryCost: 0, exitCost: 0, annualCost: 0, gainsTax: 0 };
}

export function breakEvenGrowth(plan, asset) {
  const target = projectAsset(plan, fdAsset(plan)).netWealth;
  let low = -99, high = 100;
  const at = growth => projectAsset(plan, { ...asset, growth }).netWealth;
  if (at(low) > target || at(high) < target) return null;
  for (let i = 0; i < 64; i += 1) {
    const mid = (low + high) / 2;
    if (at(mid) < target) low = mid;
    else high = mid;
  }
  return (low + high) / 2;
}

export function compareScenarios(plan, assets) {
  const benchmark = projectAsset(plan, fdAsset(plan));
  return [benchmark, ...assets.map(asset => projectAsset(plan, asset))].map(row => ({ ...row, vsFd: row.netWealth - benchmark.netWealth }));
}
