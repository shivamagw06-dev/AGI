const asArray = (value) => (Array.isArray(value) ? value : []);

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const firstText = (...values) => {
  for (const value of values) {
    if (typeof value === 'string' && value.trim()) return value.trim();
  }
  return null;
};

const key = (value) => firstText(value)?.toLowerCase().replace(/[^a-z0-9]+/g, '_') || null;

const normalizeWeight = (value) => {
  const number = finiteNumber(value);
  if (number === null || number < 0) return null;
  return number > 1 ? number / 100 : number;
};

const normalizeShock = (value) => {
  const number = finiteNumber(value);
  if (number === null) return null;
  return Math.abs(number) > 1 ? number / 100 : number;
};

const normalizeAssetClass = (value) => {
  const normalized = key(value);
  if (!normalized) return null;
  if (['stock', 'stocks', 'equity', 'equities', 'us_stock', 'indian_stock'].includes(normalized)) return 'equity';
  if (['bond', 'bonds', 'fixed_income', 'debt', 'debt_fund'].includes(normalized)) return 'fixed_income';
  if (['cash', 'cash_equivalent', 'cash_equivalents'].includes(normalized)) return 'cash';
  if (['gold', 'commodity', 'commodities'].includes(normalized)) return normalized === 'gold' ? 'gold' : 'commodity';
  if (['reit', 'real_estate'].includes(normalized)) return 'real_estate';
  return normalized;
};

const holdingIdentity = (holding, index) => ({
  id: firstText(holding.id, holding.holding_id, holding.position_id) || `holding-${index + 1}`,
  symbol: firstText(holding.symbol, holding.ticker, holding.security_symbol, holding.asset_symbol)?.toUpperCase() || null,
  name: firstText(holding.name, holding.security_name, holding.asset_name, holding.symbol, holding.ticker) || `Holding ${index + 1}`,
  assetClass: normalizeAssetClass(holding.asset_class ?? holding.assetClass ?? holding.type),
  country: key(holding.country ?? holding.domicile ?? holding.market),
  currency: key(holding.currency ?? holding.trading_currency ?? holding.base_currency),
  sector: key(holding.sector ?? holding.industry_sector ?? holding.gics_sector),
});

const normalizeHoldings = (holdings) => {
  const rows = asArray(holdings).filter((holding) => holding && typeof holding === 'object');
  const directWeights = rows.map((holding) => normalizeWeight(
    holding.effective_weight
      ?? holding.effectiveWeight
      ?? holding.portfolio_weight
      ?? holding.portfolioWeight
      ?? holding.weight
      ?? holding.allocation,
  ));
  const values = rows.map((holding) => finiteNumber(
    holding.market_value
      ?? holding.marketValue
      ?? holding.current_value
      ?? holding.currentValue
      ?? holding.value,
  ));
  const positiveValueTotal = values.reduce((total, value) => total + (value !== null && value > 0 ? value : 0), 0);

  return rows.map((holding, index) => {
    const derivedWeight = directWeights[index] !== null
      ? directWeights[index]
      : positiveValueTotal > 0 && values[index] !== null && values[index] >= 0
        ? values[index] / positiveValueTotal
        : null;
    return {
      ...holdingIdentity(holding, index),
      weight: derivedWeight,
      weightSource: directWeights[index] !== null ? 'reported' : derivedWeight !== null ? 'market_value' : 'unavailable',
    };
  });
};

const PRESETS = [
  {
    id: 'global_equity_correction',
    name: 'Global equity correction',
    description: 'Illustrative broad risk-off shock, not a forecast.',
    shocks: [
      { dimension: 'assetClass', target: 'equity', value: -0.15 },
      { dimension: 'assetClass', target: 'fixed_income', value: 0.02 },
      { dimension: 'assetClass', target: 'gold', value: 0.05 },
    ],
  },
  {
    id: 'inr_depreciation',
    name: 'INR depreciation',
    description: 'Illustrative 5% INR decline against major foreign currencies.',
    shocks: [
      { dimension: 'currency', target: 'usd', value: 0.05 },
      { dimension: 'currency', target: 'eur', value: 0.05 },
      { dimension: 'currency', target: 'gbp', value: 0.05 },
      { dimension: 'currency', target: 'jpy', value: 0.05 },
    ],
  },
  {
    id: 'technology_compression',
    name: 'Technology valuation compression',
    description: 'Illustrative sector shock across directly classified holdings.',
    shocks: [
      { dimension: 'sector', target: 'technology', value: -0.2 },
      { dimension: 'sector', target: 'information_technology', value: -0.2 },
      { dimension: 'sector', target: 'communication_services', value: -0.1 },
    ],
  },
  {
    id: 'rates_higher',
    name: 'Rates higher',
    description: 'Coarse sensitivity proxy where duration data is unavailable.',
    shocks: [
      { dimension: 'assetClass', target: 'fixed_income', value: -0.04 },
      { dimension: 'assetClass', target: 'real_estate', value: -0.06 },
      { dimension: 'assetClass', target: 'equity', value: -0.03 },
    ],
  },
];

export const PORTFOLIO_SCENARIO_PRESETS = PRESETS.map((preset) => ({ ...preset }));

const normalizeScenario = (scenario) => ({
  id: firstText(scenario?.id) || 'custom_scenario',
  name: firstText(scenario?.name) || 'Custom scenario',
  description: firstText(scenario?.description) || 'User-defined illustrative shocks.',
  shocks: asArray(scenario?.shocks).flatMap((shock) => {
    const dimension = firstText(shock?.dimension);
    const target = key(shock?.target);
    const value = normalizeShock(shock?.value);
    return dimension && target && value !== null ? [{ dimension, target, value }] : [];
  }),
});

const shocksForHolding = (holding, shocks) => asArray(shocks).filter((shock) => {
  const holdingValue = key(holding[shock.dimension]);
  return holdingValue && holdingValue === shock.target;
});

export function runPortfolioScenario({ holdings = [], scenario = PRESETS[0] } = {}) {
  const normalizedScenario = normalizeScenario(scenario);
  const normalizedHoldings = normalizeHoldings(holdings);
  const weighted = normalizedHoldings.filter((holding) => holding.weight !== null);
  const totalKnownWeight = weighted.reduce((total, holding) => total + holding.weight, 0);

  if (!normalizedHoldings.length) {
    return {
      status: 'unavailable',
      reason: 'No holdings are available for scenario analysis.',
      scenario: normalizedScenario,
      modeledImpact: null,
      coverage: null,
      contributors: [],
      affectedWeight: null,
      missing: ['holdings'],
    };
  }
  if (!weighted.length || totalKnownWeight <= 0) {
    return {
      status: 'unavailable',
      reason: 'Portfolio weights or market values are unavailable.',
      scenario: normalizedScenario,
      modeledImpact: null,
      coverage: 0,
      contributors: [],
      affectedWeight: null,
      missing: ['weights'],
    };
  }

  const contributors = weighted.map((holding) => {
    const matchedShocks = shocksForHolding(holding, normalizedScenario.shocks);
    const holdingShock = matchedShocks.reduce((total, shock) => total + shock.value, 0);
    const normalizedPortfolioWeight = holding.weight / totalKnownWeight;
    return {
      ...holding,
      normalizedPortfolioWeight,
      holdingShock,
      impact: normalizedPortfolioWeight * holdingShock,
      matchedShocks,
    };
  });
  const modeledImpact = contributors.reduce((total, holding) => total + holding.impact, 0);
  const affectedWeight = contributors
    .filter((holding) => holding.matchedShocks.length)
    .reduce((total, holding) => total + holding.normalizedPortfolioWeight, 0);
  const knownWeightCoverage = Math.min(1, totalKnownWeight);
  const missingClassification = contributors.filter((holding) => (
    normalizedScenario.shocks.some((shock) => !holding[shock.dimension])
  ));

  return {
    status: knownWeightCoverage >= 0.95 && !missingClassification.length ? 'available' : 'partial',
    reason: knownWeightCoverage < 0.95
      ? 'Some portfolio weight is unavailable.'
      : missingClassification.length
        ? 'Some holdings lack classifications required by this scenario.'
        : null,
    scenario: normalizedScenario,
    modeledImpact,
    coverage: knownWeightCoverage,
    affectedWeight,
    contributors: contributors
      .filter((holding) => holding.matchedShocks.length)
      .sort((left, right) => Math.abs(right.impact) - Math.abs(left.impact)),
    missing: [
      ...(knownWeightCoverage < 0.95 ? ['weights'] : []),
      ...(missingClassification.length ? ['classifications'] : []),
    ],
  };
}

export function buildPortfolioScenarioReport({
  holdings = [],
  scenarios = PRESETS,
  portfolioName = 'Client portfolio',
  asOf = null,
} = {}) {
  const results = asArray(scenarios).map((scenario) => runPortfolioScenario({ holdings, scenario }));
  return {
    title: `${portfolioName} - scenario review`,
    asOf: firstText(asOf) || new Date().toISOString(),
    methodology: 'Deterministic exposure shocks. Results are illustrative sensitivities, not forecasts, probabilities, or trade recommendations.',
    results,
    dataQuality: {
      available: results.filter((result) => result.status === 'available').length,
      partial: results.filter((result) => result.status === 'partial').length,
      unavailable: results.filter((result) => result.status === 'unavailable').length,
    },
  };
}

export default runPortfolioScenario;
