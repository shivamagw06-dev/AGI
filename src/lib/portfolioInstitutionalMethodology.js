export const PORTFOLIO_METHODOLOGY_VERSION = 'agi-portfolio-methodology-v2';

export const PORTFOLIO_METRIC_REQUIREMENTS = Object.freeze({
  twr: { portfolioObservations: 2 },
  xirr: { transactions: 1, elapsedDays: 30 },
  annualizedReturn: { returnObservations: 60 },
  volatility: { returnObservations: 60 },
  sharpe: { returnObservations: 60 },
  sortino: { returnObservations: 60 },
  maxDrawdown: { returnObservations: 20 },
  beta: { alignedBenchmarkObservations: 60 },
  alpha: { alignedBenchmarkObservations: 60 },
  trackingError: { alignedBenchmarkObservations: 60 },
  informationRatio: { alignedBenchmarkObservations: 60 },
  var95: { returnObservations: 60 },
  expectedShortfall95: { returnObservations: 60 },
  correlation: { alignedBenchmarkObservations: 30 },
});

const IMPACT_TYPES = Object.freeze({
  corporate_action: 'corporate_action',
  earnings: 'earnings',
  filing: 'fundamental',
  macro: 'macro',
  policy: 'macro',
  news: 'company_news',
});

function finite(value) {
  if (value === null || value === undefined || typeof value === 'boolean') return null;
  if (typeof value === 'string' && value.trim() === '') return null;
  if (typeof value === 'object') return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function text(value) {
  return String(value ?? '').trim();
}

function normalizedWeight(value) {
  const number = finite(value);
  if (number === null || number < 0) return null;
  return number > 1 ? number / 100 : number;
}

function marketValue(row) {
  const explicit = finite(row?.market_value_base ?? row?.market_value_inr ?? row?.market_value ?? row?.current_value ?? row?.value);
  if (explicit !== null) return Math.max(0, explicit);
  const quantity = finite(row?.quantity);
  const price = finite(row?.current_price ?? row?.price);
  const currency = text(row?.currency || 'INR').toUpperCase();
  const fx = currency === 'INR' ? 1 : finite(row?.fx_rate_to_inr ?? row?.fx_rate);
  return quantity !== null && price !== null && fx !== null ? Math.max(0, quantity * price * fx) : null;
}

function instrumentKey(row) {
  return text(row?.instrument_id || row?.canonical_instrument_id || row?.isin || row?.symbol || row?.id).toUpperCase();
}

function constituentParentKey(row) {
  return text(row?.fund_instrument_id || row?.parent_instrument_id || row?.fund_isin || row?.fund_symbol).toUpperCase();
}

function constituentKey(row) {
  return text(row?.constituent_instrument_id || row?.instrument_id || row?.constituent_isin || row?.isin || row?.constituent_symbol || row?.symbol).toUpperCase();
}

function constituentDate(row) {
  return text(row?.effective_date || row?.as_of_date || row?.holding_date || row?.source_as_of || row?.updated_at);
}

export function resolveBenchmarkPolicy(portfolio = {}) {
  const policy = portfolio?.benchmark_policy || {};
  const settings = portfolio?.settings || {};
  const explicit = policy.mode === 'explicit'
    || settings.benchmarkSelectionConfirmed === true
    || settings.benchmark_selection_confirmed === true
    || portfolio.benchmark_selection_confirmed === true;
  if (!explicit) {
    return {
      available: false,
      status: 'unassigned',
      components: [],
      reason: 'No benchmark has been explicitly selected for this portfolio.',
    };
  }

  const components = (Array.isArray(portfolio?.benchmark_components) ? portfolio.benchmark_components : [])
    .map((row) => ({ symbol: text(row?.symbol).toUpperCase(), weight: normalizedWeight(row?.weight) }))
    .filter((row) => row.symbol && row.weight !== null && row.weight > 0);
  const totalWeight = components.reduce((sum, row) => sum + row.weight, 0);
  if (!components.length || Math.abs(totalWeight - 1) > 0.001) {
    return {
      available: false,
      status: 'invalid',
      components: [],
      reason: 'The selected benchmark weights must be positive and sum to 100%.',
    };
  }
  return { available: true, status: 'explicit', components, reason: null };
}

export function assessMetricAvailability(metric, counts = {}) {
  const requirements = PORTFOLIO_METRIC_REQUIREMENTS[metric] || {};
  const missing = Object.entries(requirements)
    .filter(([name, minimum]) => Number(counts?.[name] || 0) < minimum)
    .map(([name, minimum]) => ({ name, minimum, actual: Number(counts?.[name] || 0) }));
  return {
    available: missing.length === 0,
    metric,
    requirements,
    missing,
    reason: missing.length
      ? `Insufficient data for ${metric}: ${missing.map((row) => `${row.name} ${row.actual}/${row.minimum}`).join(', ')}.`
      : null,
  };
}

export function buildMetricEnvelope(metric, value, counts = {}, provenance = {}) {
  const eligibility = assessMetricAvailability(metric, counts);
  const parsed = finite(value);
  const available = eligibility.available && parsed !== null;
  return {
    metric,
    value: available ? parsed : null,
    available,
    status: available ? 'available' : 'not_available',
    reason: eligibility.reason || (parsed === null ? `No valid ${metric} value was produced.` : null),
    methodologyVersion: PORTFOLIO_METHODOLOGY_VERSION,
    observationCounts: { ...counts },
    dataQuality: {
      availability: available ? 'available' : 'unavailable',
      validNumericValue: parsed !== null,
      eligibilitySatisfied: eligibility.available,
    },
    provenance: {
      sources: Array.isArray(provenance.sources) ? provenance.sources.filter(Boolean) : [],
      asOf: provenance.asOf || null,
      generatedAt: provenance.generatedAt || null,
    },
  };
}

export function buildLookThroughExposure({ holdings = [], fundConstituents = [], asOf = null } = {}) {
  const latestDateByFund = new Map();
  for (const row of fundConstituents) {
    const parent = constituentParentKey(row);
    const date = constituentDate(row);
    if (parent && date && date <= (asOf || '9999-12-31') && date > (latestDateByFund.get(parent) || '')) latestDateByFund.set(parent, date);
  }
  const constituentsByFund = new Map();
  for (const row of fundConstituents) {
    const parent = constituentParentKey(row);
    if (!parent || constituentDate(row) !== latestDateByFund.get(parent)) continue;
    const weight = normalizedWeight(row?.weight ?? row?.weight_pct ?? row?.portfolio_weight);
    const child = constituentKey(row);
    if (!child || weight === null || weight <= 0) continue;
    if (!constituentsByFund.has(parent)) constituentsByFund.set(parent, []);
    constituentsByFund.get(parent).push({ row, child, weight });
  }

  const exposureMap = new Map();
  const unresolved = [];
  let totalValue = 0;
  let resolvedValue = 0;
  let valuedHoldings = 0;

  const addExposure = (key, value, holding, constituent = null) => {
    if (!key || value <= 0) return;
    const current = exposureMap.get(key) || {
      instrumentKey: key,
      symbol: text(constituent?.constituent_symbol || constituent?.symbol || holding?.symbol).toUpperCase() || key,
      name: text(constituent?.constituent_name || constituent?.asset_name || holding?.asset_name || holding?.symbol) || key,
      marketValue: 0,
      origins: [],
    };
    current.marketValue += value;
    current.origins.push({ holdingId: holding?.id || null, holdingSymbol: holding?.symbol || null, lookThrough: Boolean(constituent) });
    exposureMap.set(key, current);
  };

  for (const holding of holdings) {
    const value = marketValue(holding);
    if (value === null) {
      unresolved.push({
        holdingId: holding?.id || null,
        symbol: holding?.symbol || null,
        marketValue: null,
        reason: 'Market value unavailable because a valid price or FX rate is missing.',
      });
      continue;
    }
    valuedHoldings += 1;
    totalValue += value;
    const key = instrumentKey(holding);
    const constituents = constituentsByFund.get(key) || constituentsByFund.get(text(holding?.symbol).toUpperCase()) || [];
    if (!constituents.length) {
      addExposure(key, value, holding);
      const isFund = ['etf', 'mutual_fund', 'fund'].includes(text(holding?.asset_type).toLowerCase());
      if (isFund && value > 0) unresolved.push({ holdingId: holding?.id || null, symbol: holding?.symbol || null, marketValue: value, reason: 'Fund constituents unavailable.' });
      else resolvedValue += value;
      continue;
    }
    const usableWeight = Math.min(1, constituents.reduce((sum, row) => sum + row.weight, 0));
    for (const constituent of constituents) addExposure(constituent.child, value * constituent.weight, holding, constituent.row);
    resolvedValue += value * usableWeight;
    if (usableWeight < 1) unresolved.push({ holdingId: holding?.id || null, symbol: holding?.symbol || null, marketValue: value * (1 - usableWeight), reason: 'Fund constituent weights are incomplete.' });
  }

  const exposures = [...exposureMap.values()]
    .map((row) => ({ ...row, portfolioWeight: totalValue > 0 ? row.marketValue / totalValue : null }))
    .sort((a, b) => b.marketValue - a.marketValue || a.instrumentKey.localeCompare(b.instrumentKey));
  return {
    available: valuedHoldings > 0,
    availability: holdings.length === 0
      ? 'unavailable'
      : valuedHoldings === holdings.length && unresolved.length === 0
        ? 'available'
        : 'partial',
    asOf,
    totalValue,
    resolvedValue,
    coveragePct: totalValue > 0 ? (resolvedValue / totalValue) * 100 : 0,
    dataQuality: {
      totalHoldings: holdings.length,
      valuedHoldings,
      valuationCoveragePct: holdings.length ? (valuedHoldings / holdings.length) * 100 : 0,
      lookThroughCoveragePct: totalValue > 0 ? (resolvedValue / totalValue) * 100 : 0,
      missingValueCount: holdings.length - valuedHoldings,
      unresolvedExposureCount: unresolved.length,
    },
    exposures,
    unresolved,
    methodologyVersion: PORTFOLIO_METHODOLOGY_VERSION,
  };
}

export function buildResearchImpactRecords({ portfolioId, userId, holdings = [], events = [], generatedAt = null } = {}) {
  const holdingBySymbol = new Map();
  const holdingByIsin = new Map();
  for (const holding of holdings) {
    if (text(holding?.symbol)) holdingBySymbol.set(text(holding.symbol).toUpperCase(), holding);
    if (text(holding?.isin)) holdingByIsin.set(text(holding.isin).toUpperCase(), holding);
  }
  return events.flatMap((event) => {
    const holding = holdingByIsin.get(text(event?.isin).toUpperCase()) || holdingBySymbol.get(text(event?.symbol).toUpperCase());
    if (!holding) return [];
    const rawDirection = text(event?.direction || event?.metadata?.direction).toLowerCase();
    const direction = ['positive', 'negative', 'mixed', 'neutral'].includes(rawDirection) ? rawDirection : null;
    const confidence = finite(event?.confidence ?? event?.metadata?.confidence);
    return [{
      portfolioId,
      userId,
      holdingId: holding.id || null,
      eventKey: text(event?.eventKey || event?.id || event?.sourceUrl),
      eventType: text(event?.eventType || 'unknown'),
      impactType: IMPACT_TYPES[event?.eventType] || 'unclassified',
      direction,
      confidence,
      status: direction ? 'classified' : 'evidence_only',
      title: text(event?.title),
      occurredAt: event?.occurredAt || null,
      evidence: {
        source: text(event?.source),
        sourceUrl: event?.sourceUrl || null,
        metadata: event?.metadata || {},
      },
      provenance: {
        methodologyVersion: PORTFOLIO_METHODOLOGY_VERSION,
        generatedAt,
        matchedBy: text(event?.isin) ? 'isin' : 'symbol',
      },
    }];
  }).filter((row) => row.eventKey);
}

function effectiveInstrumentMetadata(record = {}) {
  const instrument = record.instrument
    || record.constituent_instrument
    || record.portfolio_instruments
    || record.instruments
    || {};
  const symbol = String(
    record.constituent_symbol
      || record.symbol
      || instrument.symbol
      || instrument.ticker
      || '',
  ).trim().toUpperCase();
  return {
    instrumentKey: record.constituent_instrument_id
      || record.instrument_id
      || record.instrumentKey
      || instrument.id
      || symbol
      || null,
    symbol,
    name: record.constituent_name
      || record.asset_name
      || record.name
      || instrument.asset_name
      || instrument.name
      || symbol
      || 'Unknown',
    assetClass: record.asset_class
      || record.asset_type
      || instrument.asset_class
      || instrument.asset_type
      || 'Unknown',
    country: record.country || instrument.country || 'Unknown',
    currency: record.currency || instrument.currency || 'Unknown',
    sector: record.sector || instrument.sector || 'Unknown',
  };
}

function effectiveGroupAllocation(exposures, field) {
  const grouped = new Map();
  exposures.forEach((exposure) => {
    const value = finite(exposure.marketValue);
    if (value === null || value < 0) return;
    const label = String(exposure[field] || 'Unknown').trim() || 'Unknown';
    grouped.set(label, (grouped.get(label) || 0) + value);
  });
  const total = [...grouped.values()].reduce((sum, value) => sum + value, 0);
  if (!(total > 0)) return [];
  return [...grouped.entries()]
    .map(([label, marketValue]) => ({
      label,
      marketValue,
      weightPct: (marketValue / total) * 100,
    }))
    .sort((a, b) => b.marketValue - a.marketValue);
}

function effectiveOriginValue(origin = {}) {
  return finite(origin.marketValue ?? origin.market_value ?? origin.value ?? origin.exposureValue);
}

function effectiveSeverityRank(value) {
  return value === 'high' ? 2 : value === 'watch' ? 1 : 0;
}

export function buildEffectiveExposureAnalysis({
  holdings = [],
  fundConstituents = [],
  asOf = null,
} = {}) {
  const lookThrough = buildLookThroughExposure({ holdings, fundConstituents, asOf });
  const metadataByKey = new Map();
  const metadataBySymbol = new Map();
  [...holdings, ...fundConstituents].forEach((record) => {
    const metadata = effectiveInstrumentMetadata(record);
    if (metadata.instrumentKey) metadataByKey.set(String(metadata.instrumentKey), metadata);
    if (metadata.symbol) metadataBySymbol.set(metadata.symbol, metadata);
  });

  const exposures = (lookThrough.exposures || []).map((exposure) => {
    const symbol = String(exposure.symbol || '').trim().toUpperCase();
    const metadata = metadataByKey.get(String(exposure.instrumentKey || ''))
      || metadataBySymbol.get(symbol)
      || {};
    const origins = Array.isArray(exposure.origins) ? exposure.origins : [];
    let directMarketValue = 0;
    let lookThroughMarketValue = 0;
    let directValueObserved = false;
    let lookThroughValueObserved = false;
    origins.forEach((origin) => {
      const value = effectiveOriginValue(origin);
      if (origin.lookThrough) {
        if (value !== null) {
          lookThroughMarketValue += value;
          lookThroughValueObserved = true;
        }
      } else if (value !== null) {
        directMarketValue += value;
        directValueObserved = true;
      }
    });
    const marketValue = finite(exposure.marketValue);
    const portfolioWeight = finite(exposure.portfolioWeight);
    return {
      ...exposure,
      symbol: symbol || metadata.symbol || 'Unknown',
      name: exposure.name || metadata.name || symbol || 'Unknown',
      assetClass: metadata.assetClass || 'Unknown',
      country: metadata.country || 'Unknown',
      currency: metadata.currency || 'Unknown',
      sector: metadata.sector || 'Unknown',
      marketValue,
      weightPct: portfolioWeight === null
        ? null
        : (portfolioWeight <= 1 ? portfolioWeight * 100 : portfolioWeight),
      directMarketValue: directValueObserved ? directMarketValue : null,
      lookThroughMarketValue: lookThroughValueObserved ? lookThroughMarketValue : null,
      hasDirectOrigin: origins.some((origin) => !origin.lookThrough),
      hasLookThroughOrigin: origins.some((origin) => Boolean(origin.lookThrough)),
      originCount: origins.length,
    };
  }).sort((a, b) => (b.marketValue || 0) - (a.marketValue || 0));

  const totalValue = exposures.reduce((sum, exposure) => sum + (exposure.marketValue || 0), 0);
  const weightedExposures = exposures.map((exposure) => ({
    ...exposure,
    weightPct: exposure.weightPct === null && totalValue > 0
      ? ((exposure.marketValue || 0) / totalValue) * 100
      : exposure.weightPct,
  }));
  const allocations = {
    assetClass: effectiveGroupAllocation(weightedExposures, 'assetClass'),
    country: effectiveGroupAllocation(weightedExposures, 'country'),
    currency: effectiveGroupAllocation(weightedExposures, 'currency'),
    sector: effectiveGroupAllocation(weightedExposures, 'sector'),
  };
  const overlaps = weightedExposures
    .filter((exposure) => exposure.originCount > 1 || (exposure.hasDirectOrigin && exposure.hasLookThroughOrigin))
    .sort((a, b) => (b.weightPct || 0) - (a.weightPct || 0));
  const validWeights = weightedExposures
    .map((exposure) => finite(exposure.weightPct))
    .filter((value) => value !== null && value >= 0);
  const largestUnderlyingPct = validWeights.length ? Math.max(...validWeights) : null;
  const topFiveUnderlyingPct = validWeights.length
    ? [...validWeights].sort((a, b) => b - a).slice(0, 5).reduce((sum, value) => sum + value, 0)
    : null;
  const effectiveHhi = validWeights.length
    ? validWeights.reduce((sum, value) => sum + (value * value), 0)
    : null;

  const concentrationSignals = [];
  weightedExposures.forEach((exposure) => {
    const weight = finite(exposure.weightPct);
    if (weight === null || weight < 15) return;
    concentrationSignals.push({
      type: 'underlying',
      label: exposure.symbol || exposure.name,
      weightPct: weight,
      severity: weight >= 25 ? 'high' : 'watch',
      explanation: exposure.hasLookThroughOrigin
        ? 'Effective exposure includes one or more fund or ETF routes.'
        : 'Direct holding concentration is above the review threshold.',
    });
  });
  allocations.sector.forEach((row) => {
    if (row.weightPct < 25) return;
    concentrationSignals.push({
      type: 'sector',
      label: row.label,
      weightPct: row.weightPct,
      severity: row.weightPct >= 35 ? 'high' : 'watch',
      explanation: 'Effective sector exposure is concentrated after fund look-through.',
    });
  });
  ['country', 'currency'].forEach((type) => {
    allocations[type].forEach((row) => {
      if (row.label === 'Unknown' || row.weightPct < 60) return;
      concentrationSignals.push({
        type,
        label: row.label,
        weightPct: row.weightPct,
        severity: row.weightPct >= 75 ? 'high' : 'watch',
        explanation: `Effective ${type} exposure is above the diversification review threshold.`,
      });
    });
  });
  concentrationSignals.sort((a, b) => (
    effectiveSeverityRank(b.severity) - effectiveSeverityRank(a.severity)
      || b.weightPct - a.weightPct
  ));

  return {
    availability: lookThrough.availability || (weightedExposures.length ? 'partial' : 'unavailable'),
    asOf: lookThrough.asOf || asOf || null,
    coveragePct: finite(lookThrough.coveragePct),
    dataQuality: lookThrough.dataQuality || null,
    methodologyVersion: lookThrough.methodologyVersion || PORTFOLIO_METHODOLOGY_VERSION,
    exposures: weightedExposures,
    allocations,
    overlaps,
    concentrationSignals,
    largestUnderlyingPct,
    topFiveUnderlyingPct,
    effectiveHhi,
    unresolved: Array.isArray(lookThrough.unresolved) ? lookThrough.unresolved : [],
  };
}

export function buildInstitutionalFoundation(input = {}) {
  const benchmark = resolveBenchmarkPolicy(input.portfolio || {});
  const lookThrough = buildLookThroughExposure(input);
  const researchImpacts = buildResearchImpactRecords(input);
  return {
    methodologyVersion: PORTFOLIO_METHODOLOGY_VERSION,
    generatedAt: input.generatedAt || null,
    benchmark,
    metricRequirements: PORTFOLIO_METRIC_REQUIREMENTS,
    lookThrough,
    researchImpacts,
    warnings: [
      ...(!benchmark.available ? [benchmark.reason] : []),
      ...(lookThrough.unresolved.length ? [`${lookThrough.unresolved.length} holding exposures remain unresolved.`] : []),
    ],
  };
}
