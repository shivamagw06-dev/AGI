export const INSTITUTIONAL_ENGINE_VERSION = 'agi-institutional-portfolio-v1';

const DAY_MS = 86_400_000;
const TRADING_DAYS = 252;

const BUILT_IN_SCENARIOS = [
  {
    id: 'global_equity_selloff',
    name: 'Global equity sell-off',
    description: 'Linear first-order shock, not a full-valuation forecast.',
    asset: { indian_stock: -0.2, us_stock: -0.2, etf: -0.16, mutual_fund: -0.12 },
    currency: { USD: 0.05 },
  },
  {
    id: 'india_risk_off',
    name: 'India risk-off',
    description: 'Indian assets fall while INR weakens against USD.',
    country: { India: -0.15 },
    currency: { USD: 0.06 },
  },
  {
    id: 'us_technology_correction',
    name: 'US technology correction',
    description: 'US technology exposure receives an additional sector shock.',
    country: { 'United States': -0.08 },
    sector: { Technology: -0.17, 'Communication Services': -0.12 },
    currency: { USD: 0.02 },
  },
  {
    id: 'inr_depreciation',
    name: 'INR depreciation',
    description: 'USD assets translate 10% higher in INR; local asset prices are unchanged.',
    currency: { USD: 0.1 },
  },
  {
    id: 'liquidity_shock',
    name: 'Liquidity and gap-risk shock',
    description: 'A diagnostic haircut by asset type, not an executable liquidation estimate.',
    asset: { indian_stock: -0.12, us_stock: -0.1, etf: -0.07, mutual_fund: -0.06 },
  },
];

function number(value, fallback = 0) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function nullableNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function normalizeCountry(country, market = '') {
  const value = String(country || market || '').trim().toLowerCase();
  if (['us', 'usa', 'united states', 'united states of america', 'nasdaq', 'nyse'].includes(value)) {
    return 'United States';
  }
  if (['in', 'india', 'nse', 'bse'].includes(value)) return 'India';
  return country || 'Unknown';
}

function normalizeReturn(value) {
  const parsed = nullableNumber(value);
  if (parsed === null) return null;
  return Math.abs(parsed) > 1.5 ? parsed / 100 : parsed;
}

function ageDays(value, now) {
  if (!value) return Infinity;
  const timestamp = new Date(value).getTime();
  return Number.isFinite(timestamp) ? Math.max(0, (now.getTime() - timestamp) / DAY_MS) : Infinity;
}

function weightedGroups(positions, key) {
  const total = positions.reduce((sum, row) => sum + row.marketValueInr, 0);
  const groups = {};
  for (const row of positions) {
    const label = row[key] || 'Unknown';
    groups[label] = (groups[label] || 0) + row.marketValueInr;
  }
  return Object.entries(groups)
    .map(([name, valueInr]) => ({ name, weightPct: total > 0 ? (valueInr / total) * 100 : 0 }))
    .sort((a, b) => b.weightPct - a.weightPct);
}

function deriveLedgerCash(transactions) {
  let cash = 0;
  let hasCashEvidence = false;
  for (const transaction of transactions || []) {
    const action = String(transaction.action || '').toUpperCase();
    const fx = number(transaction.fx_rate_to_inr, 1);
    const amount = Math.abs(number(transaction.amount, number(transaction.quantity) * number(transaction.price))) * fx;
    const fees = Math.abs(number(transaction.fees)) * fx;

    if (['DEPOSIT', 'TRANSFER_IN'].includes(action)) {
      cash += Math.abs(number(transaction.external_flow_inr, amount));
      hasCashEvidence = true;
    } else if (['WITHDRAWAL', 'TRANSFER_OUT'].includes(action)) {
      cash -= Math.abs(number(transaction.external_flow_inr, amount));
      hasCashEvidence = true;
    } else if (action === 'BUY') {
      cash -= amount + fees;
      hasCashEvidence = true;
    } else if (action === 'SELL') {
      cash += amount - fees;
      hasCashEvidence = true;
    } else if (['DIVIDEND', 'INTEREST'].includes(action)) {
      cash += amount;
      hasCashEvidence = true;
    } else if (['FEE', 'TAX'].includes(action)) {
      cash -= amount;
      hasCashEvidence = true;
    }
  }
  return { valueInr: cash, status: hasCashEvidence ? 'reconciled_from_ledger' : 'not_calculable' };
}

function buildPositions(holdings, transactions, snapshots) {
  const positions = (holdings || []).map((holding) => {
    const quantity = number(holding.quantity);
    const price = number(holding.current_price);
    const fx = number(holding.fx_rate_to_inr, holding.currency === 'USD' ? 0 : 1);
    const marketValueInr = quantity * price * fx;
    return {
      id: holding.id,
      instrumentId: holding.instrument_id,
      symbol: holding.symbol || 'UNKNOWN',
      assetName: holding.asset_name || holding.symbol || 'Unknown instrument',
      assetType: holding.asset_type || 'unknown',
      country: normalizeCountry(holding.country, holding.market),
      currency: holding.currency || 'INR',
      sector: holding.sector || 'Unknown',
      marketValueInr,
      currentPrice: price,
      priceSource: holding.price_source || null,
      priceAsOf: holding.price_as_of || null,
      dataQuality: holding.data_quality || 'unknown',
    };
  }).filter((row) => row.marketValueInr >= 0);

  const ledgerCash = deriveLedgerCash(transactions);
  const latestSnapshot = [...(snapshots || [])].sort((a, b) => String(b.snapshot_date).localeCompare(String(a.snapshot_date)))[0];
  const snapshotCash = nullableNumber(latestSnapshot?.cash_value_inr);
  const cash = ledgerCash.status === 'reconciled_from_ledger'
    ? ledgerCash
    : snapshotCash !== null
      ? { valueInr: snapshotCash, status: 'reported_snapshot' }
      : ledgerCash;

  if (cash.status !== 'not_calculable') {
    positions.push({
      id: 'ledger-cash',
      instrumentId: null,
      symbol: 'CASH',
      assetName: 'Cash',
      assetType: 'cash',
      country: 'Cash',
      currency: 'INR',
      sector: 'Cash',
      marketValueInr: cash.valueInr,
      currentPrice: 1,
      priceSource: cash.status,
      priceAsOf: latestSnapshot?.snapshot_date || null,
      dataQuality: cash.status,
    });
  }

  const totalValueInr = positions.reduce((sum, row) => sum + row.marketValueInr, 0);
  return {
    positions: positions.map((row) => ({
      ...row,
      weightPct: totalValueInr > 0 ? (row.marketValueInr / totalValueInr) * 100 : 0,
    })),
    totalValueInr,
    cash,
  };
}

function returnsFromSnapshots(snapshots) {
  const ordered = [...(snapshots || [])].sort((a, b) => String(a.snapshot_date).localeCompare(String(b.snapshot_date)));
  const portfolio = [];
  const benchmark = [];
  for (let index = 1; index < ordered.length; index += 1) {
    const current = ordered[index];
    const previous = ordered[index - 1];
    let portfolioReturn = normalizeReturn(current.daily_return_pct);
    if (portfolioReturn === null) {
      const currentIndex = nullableNumber(current.portfolio_index);
      const previousIndex = nullableNumber(previous.portfolio_index);
      if (currentIndex !== null && previousIndex > 0) portfolioReturn = currentIndex / previousIndex - 1;
    }
    const currentBenchmark = nullableNumber(current.benchmark_index);
    const previousBenchmark = nullableNumber(previous.benchmark_index);
    const benchmarkReturn = currentBenchmark !== null && previousBenchmark > 0
      ? currentBenchmark / previousBenchmark - 1
      : null;
    if (portfolioReturn !== null) portfolio.push(portfolioReturn);
    if (portfolioReturn !== null && benchmarkReturn !== null) benchmark.push([portfolioReturn, benchmarkReturn]);
  }
  return { ordered, portfolio, benchmark };
}

function mean(values) {
  return values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null;
}

function sampleDeviation(values) {
  if (values.length < 2) return null;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + ((value - average) ** 2), 0) / (values.length - 1));
}

function maxDrawdown(returns) {
  if (!returns.length) return null;
  let index = 1;
  let peak = 1;
  let worst = 0;
  for (const value of returns) {
    index *= 1 + value;
    peak = Math.max(peak, index);
    worst = Math.min(worst, index / peak - 1);
  }
  return worst;
}

function performanceAnalytics(snapshots, annualRiskFreeRate) {
  const { ordered, portfolio, benchmark } = returnsFromSnapshots(snapshots);
  if (portfolio.length < 2) {
    return {
      status: 'not_calculable',
      reason: 'At least three dated portfolio snapshots are required.',
      observationCount: portfolio.length,
    };
  }

  const dailyMean = mean(portfolio);
  const dailyVolatility = sampleDeviation(portfolio);
  const downside = portfolio.filter((value) => value < 0);
  const downsideDeviation = sampleDeviation(downside);
  const dailyRiskFree = ((1 + annualRiskFreeRate) ** (1 / TRADING_DAYS)) - 1;
  const twr = portfolio.reduce((index, value) => index * (1 + value), 1) - 1;
  const annualizedReturn = ((1 + twr) ** (TRADING_DAYS / portfolio.length)) - 1;
  const annualizedVolatility = dailyVolatility === null ? null : dailyVolatility * Math.sqrt(TRADING_DAYS);
  const sharpe = annualizedVolatility > 0 ? (annualizedReturn - annualRiskFreeRate) / annualizedVolatility : null;
  const sortinoDenominator = downsideDeviation === null ? null : downsideDeviation * Math.sqrt(TRADING_DAYS);
  const sortino = sortinoDenominator > 0 ? (annualizedReturn - annualRiskFreeRate) / sortinoDenominator : null;

  let benchmarkMetrics = { status: 'not_calculable', reason: 'Aligned benchmark index history is unavailable.' };
  if (benchmark.length >= 2) {
    const portfolioAligned = benchmark.map(([value]) => value);
    const benchmarkAligned = benchmark.map(([, value]) => value);
    const pMean = mean(portfolioAligned);
    const bMean = mean(benchmarkAligned);
    const variance = benchmarkAligned.reduce((sum, value) => sum + ((value - bMean) ** 2), 0) / (benchmarkAligned.length - 1);
    const covariance = benchmarkAligned.reduce((sum, value, index) => (
      sum + ((value - bMean) * (portfolioAligned[index] - pMean))
    ), 0) / (benchmarkAligned.length - 1);
    const beta = variance > 0 ? covariance / variance : null;
    const alpha = beta === null ? null : (pMean - dailyRiskFree) - beta * (bMean - dailyRiskFree);
    const activeReturns = portfolioAligned.map((value, index) => value - benchmarkAligned[index]);
    const trackingError = sampleDeviation(activeReturns);
    benchmarkMetrics = {
      status: 'calculated',
      observationCount: benchmark.length,
      beta,
      annualizedAlpha: alpha === null ? null : alpha * TRADING_DAYS,
      annualizedTrackingError: trackingError === null ? null : trackingError * Math.sqrt(TRADING_DAYS),
      informationRatio: trackingError > 0 ? (mean(activeReturns) / trackingError) * Math.sqrt(TRADING_DAYS) : null,
    };
  }

  const sortedLosses = portfolio.map((value) => -value).sort((a, b) => a - b);
  const varIndex = Math.max(0, Math.ceil(sortedLosses.length * 0.95) - 1);
  const var95 = portfolio.length >= 60 ? sortedLosses[varIndex] : null;
  const tail = var95 === null ? [] : sortedLosses.filter((value) => value >= var95);

  return {
    status: 'calculated',
    startDate: ordered[0]?.snapshot_date,
    endDate: ordered.at(-1)?.snapshot_date,
    observationCount: portfolio.length,
    twr,
    annualizedReturn,
    annualizedVolatility,
    sharpe,
    sortino,
    maxDrawdown: maxDrawdown(portfolio),
    historicalVar95: var95,
    expectedShortfall95: tail.length ? mean(tail) : null,
    tailRiskStatus: portfolio.length >= 60 ? 'calculated' : 'not_calculable',
    tailRiskReason: portfolio.length >= 60 ? null : '60 daily observations are required for historical tail-risk statistics.',
    benchmark: benchmarkMetrics,
  };
}

function latestFundRows(rows) {
  const latestDate = {};
  for (const row of rows || []) {
    const fund = row.fund_instrument_id;
    if (!latestDate[fund] || String(row.as_of_date) > latestDate[fund]) latestDate[fund] = String(row.as_of_date);
  }
  return (rows || []).filter((row) => String(row.as_of_date) === latestDate[row.fund_instrument_id]);
}

function lookThroughAnalytics(positions, fundConstituents, constituentInstruments) {
  const fundRows = latestFundRows(fundConstituents);
  const instruments = Object.fromEntries((constituentInstruments || []).map((row) => [row.id, row]));
  const rowsByFund = {};
  for (const row of fundRows) {
    rowsByFund[row.fund_instrument_id] ||= [];
    rowsByFund[row.fund_instrument_id].push(row);
  }

  const direct = {};
  let fundWeight = 0;
  let resolvedFundWeight = 0;
  for (const position of positions) {
    if (!['mutual_fund', 'etf'].includes(position.assetType)) {
      direct[position.instrumentId || position.symbol] = (direct[position.instrumentId || position.symbol] || 0) + position.weightPct;
      continue;
    }
    fundWeight += position.weightPct;
    const constituents = rowsByFund[position.instrumentId] || [];
    const disclosedWeight = constituents.reduce((sum, row) => sum + number(row.weight_pct), 0);
    if (!constituents.length || disclosedWeight <= 0) continue;
    resolvedFundWeight += position.weightPct * Math.min(disclosedWeight, 100) / 100;
    for (const constituent of constituents) {
      const key = constituent.constituent_instrument_id;
      direct[key] = (direct[key] || 0) + position.weightPct * number(constituent.weight_pct) / 100;
    }
  }

  const overlap = Object.entries(direct)
    .map(([key, weightPct]) => ({
      instrumentId: key,
      symbol: instruments[key]?.symbol || positions.find((row) => (row.instrumentId || row.symbol) === key)?.symbol || key,
      assetName: instruments[key]?.asset_name || positions.find((row) => (row.instrumentId || row.symbol) === key)?.assetName || key,
      weightPct,
    }))
    .sort((a, b) => b.weightPct - a.weightPct);

  return {
    status: fundWeight === 0 ? 'not_applicable' : resolvedFundWeight > 0 ? 'partial' : 'not_calculable',
    fundWeightPct: fundWeight,
    resolvedFundWeightPct: resolvedFundWeight,
    coveragePct: fundWeight > 0 ? (resolvedFundWeight / fundWeight) * 100 : 100,
    topUnderlyingHoldings: overlap.slice(0, 15),
    reason: fundWeight > 0 && resolvedFundWeight === 0
      ? 'No dated, sourced constituent file is available for the portfolio funds.'
      : null,
  };
}

function corporateActionDiagnostics(positions, corporateActions, transactions) {
  const heldInstruments = new Set(positions.map((row) => row.instrumentId).filter(Boolean));
  const relevant = (corporateActions || []).filter((row) => heldInstruments.has(row.instrument_id));
  const reconciled = [];
  const unreconciled = [];
  for (const action of relevant) {
    const actionDate = action.ex_date || action.record_date || action.payable_date;
    const type = String(action.action_type || '').toUpperCase();
    const match = (transactions || []).some((transaction) => {
      if (transaction.instrument_id !== action.instrument_id) return false;
      const transactionType = String(transaction.action || '').toUpperCase();
      if (type.includes('DIVIDEND') && transactionType !== 'DIVIDEND') return false;
      if (type.includes('SPLIT') && transactionType !== 'SPLIT') return false;
      if (!actionDate) return true;
      return Math.abs(new Date(transaction.trade_date).getTime() - new Date(actionDate).getTime()) <= 45 * DAY_MS;
    });
    (match ? reconciled : unreconciled).push(action);
  }
  return {
    status: relevant.length ? (unreconciled.length ? 'review_required' : 'reconciled') : 'no_sourced_actions',
    sourcedCount: relevant.length,
    reconciledCount: reconciled.length,
    unreconciled,
  };
}

function scenarioAnalytics(positions, scenarios = BUILT_IN_SCENARIOS) {
  return scenarios.map((scenario) => {
    let impactPct = 0;
    let mappedWeightPct = 0;
    const contributors = [];
    for (const position of positions) {
      if (position.assetType === 'cash') continue;
      const shocks = [
        scenario.asset?.[position.assetType],
        scenario.country?.[position.country],
        scenario.sector?.[position.sector],
        scenario.currency?.[position.currency],
      ].filter((value) => Number.isFinite(value));
      if (!shocks.length) continue;
      mappedWeightPct += position.weightPct;
      const shock = shocks.reduce((sum, value) => sum + value, 0);
      const contribution = (position.weightPct / 100) * shock;
      impactPct += contribution;
      contributors.push({ symbol: position.symbol, shock, contribution });
    }
    return {
      id: scenario.id,
      name: scenario.name,
      description: scenario.description,
      methodology: 'linear first-order exposure shock',
      impactPct,
      mappedWeightPct,
      confidence: mappedWeightPct >= 80 ? 'high' : mappedWeightPct >= 50 ? 'medium' : 'low',
      topContributors: contributors.sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution)).slice(0, 5),
    };
  });
}

function policyAnalytics(positions, policy) {
  const assetTargets = policy?.asset_targets || policy?.assetTargets;
  if (!assetTargets || !Object.keys(assetTargets).length) {
    return {
      status: 'not_calculable',
      reason: 'No client-approved strategic allocation policy has been configured.',
      suggestedTrades: [],
    };
  }
  const allocation = Object.fromEntries(weightedGroups(positions, 'assetType').map((row) => [row.name, row.weightPct]));
  const drift = Object.entries(assetTargets).map(([assetType, target]) => {
    const targetPct = number(target);
    const currentPct = number(allocation[assetType]);
    return { assetType, currentPct, targetPct, driftPct: currentPct - targetPct };
  });
  const tolerance = number(policy.rebalance_tolerance_pct, 5);
  return {
    status: 'calculated',
    methodology: 'asset-class drift against a client-approved policy; no security recommendation is generated',
    tolerancePct: tolerance,
    drift,
    breaches: drift.filter((row) => Math.abs(row.driftPct) > tolerance),
    suggestedTrades: [],
  };
}

function coverageAnalytics(positions, snapshots, lookThrough, now) {
  const investable = positions.filter((row) => row.assetType !== 'cash');
  const investableWeight = investable.reduce((sum, row) => sum + row.weightPct, 0) || 1;
  const weighted = (predicate) => investable.reduce((sum, row) => sum + (predicate(row) ? row.weightPct : 0), 0) / investableWeight * 100;
  const identityPct = weighted((row) => Boolean(row.instrumentId));
  const sourcedPricePct = weighted((row) => Boolean(row.priceSource));
  const freshPricePct = weighted((row) => row.currentPrice > 0 && ageDays(row.priceAsOf, now) <= 4);
  const historyPct = clamp(((snapshots || []).length / 60) * 100, 0, 100);
  const lookThroughPct = lookThrough.status === 'not_applicable' ? 100 : lookThrough.coveragePct;
  const score = identityPct * 0.25 + sourcedPricePct * 0.2 + freshPricePct * 0.25 + historyPct * 0.2 + lookThroughPct * 0.1;
  return {
    score,
    grade: score >= 90 ? 'A' : score >= 75 ? 'B' : score >= 55 ? 'C' : score >= 35 ? 'D' : 'E',
    identityPct,
    sourcedPricePct,
    freshPricePct,
    historyPct,
    fundLookThroughPct: lookThroughPct,
    snapshotCount: (snapshots || []).length,
  };
}

function buildAlerts(positions, performance, coverage, lookThrough, corporateActions, policy) {
  const alerts = [];
  const push = (alertKey, severity, title, detail, evidence = {}) => alerts.push({ alertKey, severity, title, detail, evidence });
  const top = [...positions].filter((row) => row.assetType !== 'cash').sort((a, b) => b.weightPct - a.weightPct)[0];
  if (top?.weightPct > 25) push('single_position_concentration', 'high', 'Single-position concentration', `${top.symbol} represents ${top.weightPct.toFixed(1)}% of the portfolio.`, { thresholdPct: 25, observedPct: top.weightPct });
  if (coverage.freshPricePct < 95) push('stale_price_coverage', 'high', 'Price freshness below threshold', `${coverage.freshPricePct.toFixed(1)}% of investable value has a sourced price no older than four days.`, { thresholdPct: 95 });
  if (coverage.identityPct < 100) push('identity_coverage', 'high', 'Instrument identity incomplete', `${coverage.identityPct.toFixed(1)}% of investable value is linked to the canonical security master.`, { thresholdPct: 100 });
  if (performance.status !== 'calculated') push('performance_history', 'watch', 'Performance history is still accumulating', performance.reason, { observations: performance.observationCount });
  if (lookThrough.status === 'not_calculable') push('fund_lookthrough', 'watch', 'Fund look-through unavailable', lookThrough.reason, { fundWeightPct: lookThrough.fundWeightPct });
  if (corporateActions.unreconciled.length) push('corporate_actions', 'high', 'Corporate actions require reconciliation', `${corporateActions.unreconciled.length} sourced action(s) are not matched to the transaction ledger.`, { count: corporateActions.unreconciled.length });
  if (policy.status !== 'calculated') push('allocation_policy', 'watch', 'Strategic allocation policy not configured', policy.reason);
  return alerts;
}

export function buildInstitutionalPortfolioReport({
  portfolio,
  holdings = [],
  transactions = [],
  snapshots = [],
  fundConstituents = [],
  constituentInstruments = [],
  corporateActions = [],
  policy = null,
  now = new Date(),
}) {
  const positionBook = buildPositions(holdings, transactions, snapshots);
  const allocations = {
    assetClass: weightedGroups(positionBook.positions, 'assetType'),
    country: weightedGroups(positionBook.positions, 'country'),
    currency: weightedGroups(positionBook.positions, 'currency'),
    sector: weightedGroups(positionBook.positions, 'sector'),
  };
  const performance = performanceAnalytics(snapshots, number(portfolio?.risk_free_rate, 0.065));
  const lookThrough = lookThroughAnalytics(positionBook.positions, fundConstituents, constituentInstruments);
  const actions = corporateActionDiagnostics(positionBook.positions, corporateActions, transactions);
  const policyResult = policyAnalytics(positionBook.positions, policy);
  const coverage = coverageAnalytics(positionBook.positions, snapshots, lookThrough, now);
  const scenarios = scenarioAnalytics(positionBook.positions);
  const alerts = buildAlerts(positionBook.positions, performance, coverage, lookThrough, actions, policyResult);

  return {
    engineVersion: INSTITUTIONAL_ENGINE_VERSION,
    generatedAt: now.toISOString(),
    methodology: {
      standard: 'AGI evidence-aware institutional portfolio workflow',
      principles: [
        'transaction-led cash and performance',
        'benchmark-aligned returns only',
        'dated holdings for fund look-through',
        'linear scenarios disclosed as diagnostics',
        'missing evidence returns not_calculable',
      ],
      notIncluded: ['licensed Barra/Aladdin/Bloomberg factor models', 'personalized investment advice', 'tax advice'],
    },
    totalValueInr: positionBook.totalValueInr,
    cash: positionBook.cash,
    positions: positionBook.positions,
    allocations,
    performance,
    lookThrough,
    corporateActions: actions,
    factorRisk: {
      status: 'not_calculable',
      reason: 'A calibrated factor-return history and security exposure matrix are required; sector and country allocation are shown separately and are not labelled as factor risk.',
    },
    brinsonAttribution: {
      status: 'not_calculable',
      reason: 'Dated benchmark constituent weights and aligned sector returns are required.',
    },
    scenarios,
    policy: policyResult,
    coverage,
    alerts,
  };
}

