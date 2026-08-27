const TRADING_DAYS = 252;

const num = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const mean = (values) => values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : 0;

const stdev = (values) => {
  if (values.length < 2) return 0;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + ((value - average) ** 2), 0) / (values.length - 1));
};

const covariance = (left, right) => {
  const length = Math.min(left.length, right.length);
  if (length < 2) return 0;
  const a = left.slice(-length);
  const b = right.slice(-length);
  const ma = mean(a);
  const mb = mean(b);
  return a.reduce((sum, value, index) => sum + ((value - ma) * (b[index] - mb)), 0) / (length - 1);
};

const percentile = (values, p) => {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.max(0, Math.floor((sorted.length - 1) * p)));
  return sorted[index];
};

function maximumDrawdown(returns) {
  let wealth = 1;
  let peak = 1;
  let worst = 0;
  const curve = [];
  returns.forEach((value) => {
    wealth *= 1 + value;
    peak = Math.max(peak, wealth);
    const drawdown = (wealth / peak) - 1;
    worst = Math.min(worst, drawdown);
    curve.push(drawdown * 100);
  });
  return { value: worst * 100, curve };
}

function xirr(cashflows) {
  const flows = cashflows.filter((row) => Number.isFinite(row.amount) && row.date instanceof Date && Number.isFinite(row.date.getTime()));
  if (flows.length < 2 || !flows.some((row) => row.amount < 0) || !flows.some((row) => row.amount > 0)) return null;
  const start = Math.min(...flows.map((row) => row.date.getTime()));
  const npv = (rate) => flows.reduce((sum, row) => sum + row.amount / ((1 + rate) ** ((row.date.getTime() - start) / 31_557_600_000)), 0);
  let low = -0.9999;
  let high = 10;
  let lowValue = npv(low);
  let highValue = npv(high);
  for (let extension = 0; lowValue * highValue > 0 && extension < 8; extension += 1) {
    high *= 2;
    highValue = npv(high);
  }
  if (lowValue * highValue > 0) return null;
  for (let iteration = 0; iteration < 120; iteration += 1) {
    const mid = (low + high) / 2;
    const value = npv(mid);
    if (Math.abs(value) < 0.0001) return mid * 100;
    if (lowValue * value <= 0) high = mid;
    else {
      low = mid;
      lowValue = value;
    }
  }
  return ((low + high) / 2) * 100;
}

function timeWeightedReturn(snapshots) {
  if (snapshots.length < 2) return null;
  let growth = 1;
  for (let index = 1; index < snapshots.length; index += 1) {
    const prior = num(snapshots[index - 1].total_value_inr);
    const current = num(snapshots[index].total_value_inr);
    const flow = num(snapshots[index].net_external_flow_inr);
    if (prior > 0) growth *= 1 + ((current - flow - prior) / prior);
  }
  return (growth - 1) * 100;
}

function dateReturnMap(rows = []) {
  return new Map(rows.filter((row) => row.date && Number.isFinite(Number(row.returnPct))).map((row) => [row.date, Number(row.returnPct) / 100]));
}

function alignedPortfolioReturns(positions, marketPackage) {
  const maps = positions.map((position) => ({
    weight: position.weight,
    map: dateReturnMap(marketPackage?.instruments?.[position.id]?.returns),
  })).filter((row) => row.map.size);
  if (!maps.length) return { dates: [], returns: [] };
  const dateCounts = new Map();
  maps.forEach((row) => row.map.forEach((_value, date) => dateCounts.set(date, (dateCounts.get(date) || 0) + 1)));
  const requiredCoverage = Math.max(1, Math.ceil(maps.length * 0.6));
  const dates = [...dateCounts.entries()].filter(([, count]) => count >= requiredCoverage).map(([date]) => date).sort();
  return {
    dates,
    returns: dates.map((date) => {
      let weighted = 0;
      let coveredWeight = 0;
      maps.forEach((row) => {
        if (!row.map.has(date)) return;
        weighted += row.weight * row.map.get(date);
        coveredWeight += row.weight;
      });
      // Do not renormalize away cash or positions without history. Their weight
      // remains part of the portfolio even when they contribute a zero return.
      return coveredWeight ? weighted : 0;
    }),
  };
}

function benchmarkReturns(marketPackage, components) {
  const maps = (components || []).map((component) => ({
    weight: num(component.weight),
    map: dateReturnMap(marketPackage?.benchmarks?.[component.symbol]?.returns),
  })).filter((row) => row.map.size && row.weight > 0);
  const dates = [...new Set(maps.flatMap((row) => [...row.map.keys()]))].sort();
  const byDate = new Map(dates.map((date) => {
    let value = 0;
    let weight = 0;
    maps.forEach((row) => {
      if (!row.map.has(date)) return;
      value += row.weight * row.map.get(date);
      weight += row.weight;
    });
    return [date, weight ? value / weight : 0];
  }));
  return byDate;
}

function allocation(positions, key) {
  const values = new Map();
  positions.forEach((position) => {
    const label = position[key] || 'Other';
    values.set(label, (values.get(label) || 0) + position.currentValue);
  });
  const total = positions.reduce((sum, row) => sum + row.currentValue, 0);
  return [...values.entries()].map(([label, value]) => ({ label, value, weight: total ? (value / total) * 100 : 0 })).sort((a, b) => b.value - a.value);
}

function factorExposures(positions, beta) {
  const total = positions.reduce((sum, row) => sum + row.currentValue, 0) || 1;
  const weight = (predicate) => positions.filter(predicate).reduce((sum, row) => sum + row.currentValue, 0) / total;
  return [
    { name: 'Market beta', score: beta, basis: 'Return history versus the blended benchmark' },
    { name: 'India equity', score: weight((row) => row.country === 'India' && row.asset_type !== 'cash'), basis: 'Country and asset classification' },
    { name: 'US equity', score: weight((row) => row.country === 'US' && row.asset_type !== 'cash'), basis: 'Country and asset classification' },
    { name: 'Growth / technology', score: weight((row) => /tech|internet|communication/i.test(row.sector || '')), basis: 'Sector proxy; not a fitted factor model' },
    { name: 'Financials', score: weight((row) => /financial|bank|capital market/i.test(row.sector || '')), basis: 'Sector proxy; not a fitted factor model' },
    { name: 'Cash defence', score: weight((row) => row.asset_type === 'cash'), basis: 'Direct cash weight' },
  ];
}

function normalizedCountry(country, currency) {
  const value = String(country || '').trim().toUpperCase();
  if (currency === 'USD' || ['US', 'USA', 'UNITED STATES', 'UNITED STATES OF AMERICA'].includes(value)) return 'US';
  if (value === 'INDIA' || (!value && currency === 'INR')) return 'India';
  return country || 'Other';
}

function transactionCashBalance(transactions) {
  const externalActions = new Set(['DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT']);
  const hasExplicitCashLedger = transactions.some((row) => externalActions.has(String(row.action || '').toUpperCase()));
  if (!hasExplicitCashLedger) return { value: null, source: 'holdings', hasExplicitCashLedger: false };

  const value = transactions.reduce((cash, row) => {
    const action = String(row.action || '').toUpperCase();
    const fx = num(row.fx_rate_to_inr, 1);
    const gross = Math.abs(num(row.amount, num(row.quantity) * num(row.price))) * fx;
    const fees = Math.abs(num(row.fees)) * fx;
    if (['DEPOSIT', 'TRANSFER_IN', 'DIVIDEND', 'INTEREST'].includes(action)) return cash + gross - fees;
    if (['WITHDRAWAL', 'TRANSFER_OUT', 'BUY'].includes(action)) return cash - gross - fees;
    if (action === 'SELL') return cash + gross - fees;
    if (['FEE', 'TAX'].includes(action)) return cash - gross - fees;
    return cash;
  }, 0);
  return { value: Math.abs(value) < 0.005 ? 0 : value, source: 'transaction_ledger', hasExplicitCashLedger: true };
}

function growthIndex(returns) {
  return returns.reduce((wealth, value) => wealth * (1 + num(value)), 100);
}

export function buildPortfolioAnalytics({ holdings = [], transactions = [], snapshots = [], portfolio, marketPackage }) {
  const positions = holdings.map((holding) => {
    const market = marketPackage?.instruments?.[holding.id] || {};
    const effectivePrice = num(market.price, num(holding.current_price, num(holding.average_cost)));
    const effectiveFx = holding.currency === 'USD' ? num(marketPackage?.fx?.usdInr?.price, num(holding.fx_rate_to_inr, 1)) : 1;
    const costFx = holding.currency === 'USD' ? num(holding.fx_rate_to_inr, effectiveFx) : 1;
    const investedValue = num(holding.quantity) * num(holding.average_cost) * costFx;
    const currentValue = num(holding.quantity) * effectivePrice * effectiveFx;
    return {
      ...holding,
      country: normalizedCountry(holding.country, holding.currency),
      effectivePrice,
      effectiveFx,
      investedValue,
      currentValue,
      gain: currentValue - investedValue,
      gainPct: investedValue ? ((currentValue / investedValue) - 1) * 100 : 0,
      priceSource: market.source || holding.price_source || 'manual',
      priceAsOf: market.asOf || holding.price_as_of || null,
      priceQuality: market.quality || holding.data_quality || 'manual',
      dailyChangePct: market.changePct,
      fundamentals: market.fundamentals || null,
    };
  });
  const securityValue = positions.filter((row) => row.asset_type !== 'cash').reduce((sum, row) => sum + row.currentValue, 0);
  const directCashValue = positions.filter((row) => row.asset_type === 'cash').reduce((sum, row) => sum + row.currentValue, 0);
  const ledgerCash = transactionCashBalance(transactions);
  const cashValue = ledgerCash.value == null ? directCashValue : ledgerCash.value;
  const totalValue = securityValue + cashValue;
  const investedValue = positions.filter((row) => row.asset_type !== 'cash').reduce((sum, row) => sum + row.investedValue, 0);
  positions.forEach((row) => { row.weight = totalValue ? row.currentValue / totalValue : 0; row.weightPct = row.weight * 100; });
  const cashExposure = cashValue ? [{
    id: 'ledger-cash', symbol: 'CASH', asset_name: 'Cash ledger', asset_type: 'cash', market: 'CASH',
    country: 'India', currency: 'INR', sector: 'Cash', currentValue: cashValue,
    investedValue: 0, gain: 0, gainPct: 0, effectivePrice: 1, effectiveFx: 1,
    weight: totalValue ? cashValue / totalValue : 0, weightPct: totalValue ? (cashValue / totalValue) * 100 : 0,
    priceSource: ledgerCash.source, priceQuality: 'ledger', priceAsOf: new Date().toISOString(),
  }] : [];
  const exposurePositions = [...positions.filter((row) => row.asset_type !== 'cash'), ...cashExposure];
  const hhi = exposurePositions.reduce((sum, row) => sum + (row.weight ** 2), 0);
  const topFive = [...exposurePositions].sort((a, b) => b.currentValue - a.currentValue).slice(0, 5).reduce((sum, row) => sum + row.weightPct, 0);

  const portfolioSeries = alignedPortfolioReturns(positions, marketPackage);
  const benchmarkMap = benchmarkReturns(marketPackage, portfolio?.benchmark_components || [{ symbol: 'NIFTY', weight: 0.6 }, { symbol: '^GSPC', weight: 0.4 }]);
  const aligned = portfolioSeries.dates.filter((date) => benchmarkMap.has(date));
  const portfolioReturns = aligned.map((date) => portfolioSeries.returns[portfolioSeries.dates.indexOf(date)]);
  const benchmark = aligned.map((date) => benchmarkMap.get(date));
  const annualReturn = portfolioReturns.length ? ((portfolioReturns.reduce((wealth, value) => wealth * (1 + value), 1) ** (TRADING_DAYS / portfolioReturns.length)) - 1) : 0;
  const volatility = stdev(portfolioReturns) * Math.sqrt(TRADING_DAYS);
  const downside = stdev(portfolioReturns.filter((value) => value < 0)) * Math.sqrt(TRADING_DAYS);
  const riskFree = num(portfolio?.risk_free_rate, 0.065);
  const beta = benchmark.length && stdev(benchmark) ? covariance(portfolioReturns, benchmark) / (stdev(benchmark) ** 2) : null;
  const drawdown = maximumDrawdown(portfolioReturns);
  const varDaily = percentile(portfolioReturns, 0.05);
  const tail = portfolioReturns.filter((value) => value <= varDaily);
  const expectedShortfall = tail.length ? mean(tail) : varDaily;

  const cashflows = transactions
    .filter((row) => num(row.external_flow_inr) !== 0)
    .map((row) => ({ date: new Date(`${row.trade_date}T00:00:00`), amount: -num(row.external_flow_inr) }));
  if (totalValue > 0) cashflows.push({ date: new Date(), amount: totalValue });
  const xirrPct = xirr(cashflows);
  const twrPct = timeWeightedReturn(snapshots);

  const attribution = positions.map((row) => ({
    symbol: row.symbol,
    name: row.asset_name,
    weightPct: row.weightPct,
    returnPct: row.gainPct,
    contributionPct: row.weight * row.gainPct,
    fxContributionPct: row.currency === 'USD' ? ((row.effectiveFx / num(row.fx_rate_to_inr, row.effectiveFx)) - 1) * row.weight * 100 : 0,
  })).sort((a, b) => b.contributionPct - a.contributionPct);

  const correlations = positions.filter((row) => (marketPackage?.instruments?.[row.id]?.returns || []).length >= 20).slice(0, 10).map((left) => {
    const leftMap = dateReturnMap(marketPackage.instruments[left.id].returns);
    return {
      symbol: left.symbol,
      values: positions.filter((row) => (marketPackage?.instruments?.[row.id]?.returns || []).length >= 20).slice(0, 10).map((right) => {
        const rightMap = dateReturnMap(marketPackage.instruments[right.id].returns);
        const dates = [...leftMap.keys()].filter((date) => rightMap.has(date));
        const a = dates.map((date) => leftMap.get(date));
        const b = dates.map((date) => rightMap.get(date));
        const denominator = stdev(a) * stdev(b);
        return denominator ? covariance(a, b) / denominator : (left.id === right.id ? 1 : 0);
      }),
    };
  });

  const pricedPositions = positions.filter((row) => row.asset_type !== 'cash');
  const covered = pricedPositions.filter((row) => ['live', 'observed'].includes(row.priceQuality)).length;
  const identified = pricedPositions.filter((row) => row.instrument_id || row.provider_key || row.isin).length;
  const sourced = pricedPositions.filter((row) => row.priceSource && row.priceSource !== 'manual').length;
  const timestamped = pricedPositions.filter((row) => row.priceAsOf).length;
  const funds = pricedPositions.filter((row) => row.asset_type === 'mutual_fund');
  const observedFunds = funds.filter((row) => ['live', 'observed'].includes(row.priceQuality)).length;
  const historyDays = portfolioReturns.length;
  const priceCoveragePct = pricedPositions.length ? (covered / pricedPositions.length) * 100 : 100;
  const identifierCoveragePct = pricedPositions.length ? (identified / pricedPositions.length) * 100 : 100;
  const sourceCoveragePct = pricedPositions.length ? (sourced / pricedPositions.length) * 100 : 100;
  const timestampCoveragePct = pricedPositions.length ? (timestamped / pricedPositions.length) * 100 : 100;
  const issues = [];
  if (priceCoveragePct < 100) issues.push(`${(100 - priceCoveragePct).toFixed(0)}% of holdings use manual or fallback prices.`);
  if (identifierCoveragePct < 100) issues.push(`${(100 - identifierCoveragePct).toFixed(0)}% of holdings lack a durable market identifier.`);
  if (cashValue < 0) issues.push('The transaction ledger has a negative cash balance; review funding or margin activity.');
  if (!ledgerCash.hasExplicitCashLedger && transactions.some((row) => ['BUY', 'SELL'].includes(String(row.action || '').toUpperCase()))) issues.push('No explicit deposit or transfer ledger exists, so cash is sourced from cash holdings only.');
  if (funds.length && observedFunds < funds.length) issues.push('One or more mutual-fund NAVs remain manual.');
  if (snapshots.length < 2) issues.push('At least two daily snapshots are required for TWR.');
  const grade = cashValue < 0 || priceCoveragePct < 50 ? 'D'
    : priceCoveragePct >= 95 && identifierCoveragePct >= 90 && historyDays >= 120 && snapshots.length >= 2 ? 'A'
      : priceCoveragePct >= 80 && historyDays >= 60 ? 'B' : 'C';
  const portfolioIndex = growthIndex(portfolioReturns);
  const benchmarkIndex = growthIndex(benchmark);
  const dailyReturn = portfolioReturns.length ? portfolioReturns.at(-1) * 100 : null;
  const currentDay = new Date().toISOString().slice(0, 10);
  const externalFlow = transactions.filter((row) => String(row.trade_date || '').slice(0, 10) === currentDay).reduce((sum, row) => sum + num(row.external_flow_inr), 0);
  return {
    positions,
    totalValue,
    securityValue,
    investedValue,
    gain: securityValue - investedValue,
    gainPct: investedValue ? ((securityValue / investedValue) - 1) * 100 : 0,
    cashValue,
    cashSource: ledgerCash.source,
    externalFlow,
    dailyReturn,
    portfolioIndex,
    benchmarkIndex,
    hhi,
    concentration: hhi >= 0.25 ? 'High' : hhi >= 0.15 ? 'Moderate' : 'Diversified',
    largestPositionPct: Math.max(0, ...positions.map((row) => row.weightPct)),
    topFivePct: topFive,
    allocation: {
      asset: allocation(exposurePositions, 'asset_type'),
      sector: allocation(exposurePositions, 'sector'),
      country: allocation(exposurePositions, 'country'),
      currency: allocation(exposurePositions, 'currency'),
    },
    performance: {
      twrPct,
      xirrPct,
      costReturnPct: investedValue ? ((securityValue / investedValue) - 1) * 100 : 0,
      annualizedReturnPct: annualReturn * 100,
      observations: portfolioReturns.length,
      attribution,
    },
    risk: {
      volatilityPct: volatility * 100,
      beta,
      sharpe: volatility ? (annualReturn - riskFree) / volatility : null,
      sortino: downside ? (annualReturn - riskFree) / downside : null,
      maxDrawdownPct: drawdown.value,
      var95Pct: varDaily * 100,
      expectedShortfall95Pct: expectedShortfall * 100,
      drawdownCurve: drawdown.curve,
      correlations,
    },
    factors: factorExposures(exposurePositions, beta),
    dataQuality: {
      priceCoveragePct,
      identifierCoveragePct,
      sourceCoveragePct,
      timestampCoveragePct,
      fundNavCoveragePct: funds.length ? (observedFunds / funds.length) * 100 : 100,
      cashStatus: ledgerCash.hasExplicitCashLedger ? (cashValue < 0 ? 'negative' : 'reconciled') : 'holdings_only',
      historyObservations: historyDays,
      transactionCount: transactions.length,
      snapshotCount: snapshots.length,
      issues,
      grade,
    },
    series: { dates: aligned, portfolioReturns, benchmarkReturns: benchmark },
  };
}

export function runPortfolioScenario(analytics, assumptions) {
  const countryShocks = assumptions.country || {};
  const sectorShocks = assumptions.sector || {};
  const assetShocks = assumptions.asset || {};
  const currencyShocks = assumptions.currency || {};
  const positions = analytics.positions.map((position) => {
    const assetShock = num(assetShocks[position.asset_type]);
    const countryShock = num(countryShocks[position.country]);
    const sectorShock = num(sectorShocks[position.sector]);
    const fxShock = position.currency === 'USD' ? num(currencyShocks.USD) : 0;
    const combined = ((1 + assetShock / 100) * (1 + countryShock / 100) * (1 + sectorShock / 100) * (1 + fxShock / 100)) - 1;
    return { symbol: position.symbol, impact: position.currentValue * combined, impactPct: combined * 100 };
  });
  const impact = positions.reduce((sum, row) => sum + row.impact, 0);
  return {
    impact,
    impactPct: analytics.totalValue ? (impact / analytics.totalValue) * 100 : 0,
    stressedValue: analytics.totalValue + impact,
    positions: positions.sort((a, b) => a.impact - b.impact),
  };
}

export const presetScenarios = [
  { name: 'Global risk-off', assumptions: { asset: { indian_stock: -12, us_stock: -14, etf: -10, mutual_fund: -7 }, currency: { USD: 4 } } },
  { name: 'India rate shock', assumptions: { country: { India: -8 }, sector: { Financials: -12, 'Real Estate': -15 }, currency: { USD: 3 } } },
  { name: 'US technology correction', assumptions: { country: { US: -10 }, sector: { Technology: -18, 'Communication Services': -14 }, currency: { USD: -2 } } },
  { name: 'Rupee depreciation', assumptions: { currency: { USD: 8 } } },
];

export function answerPortfolioQuestion(question, analytics, events = []) {
  const query = String(question || '').toLowerCase();
  if (!query.trim()) return 'Ask about risk, concentration, performance, currency exposure, scenarios, or what changed today.';
  const top = analytics.positions.slice().sort((a, b) => b.currentValue - a.currentValue)[0];
  if (/risk|safe|danger|drawdown|var/.test(query)) {
    return `Risk is ${analytics.concentration.toLowerCase()} by concentration. Estimated annualized volatility is ${analytics.risk.volatilityPct.toFixed(1)}%, maximum observed drawdown is ${analytics.risk.maxDrawdownPct.toFixed(1)}%, and one-day 95% historical VaR is ${Math.abs(analytics.risk.var95Pct).toFixed(1)}%. These estimates use ${analytics.performance.observations} aligned daily observations.`;
  }
  if (/concentr|largest|top holding/.test(query)) {
    return top ? `${top.asset_name} is the largest position at ${top.weightPct.toFixed(1)}%. The top five positions represent ${analytics.topFivePct.toFixed(1)}% and portfolio HHI is ${analytics.hhi.toFixed(3)}.` : 'There are no positions to assess.';
  }
  if (/perform|return|profit|gain|xirr|twr/.test(query)) {
    const xirrText = analytics.performance.xirrPct == null ? 'XIRR needs dated cash flows' : `XIRR is ${analytics.performance.xirrPct.toFixed(1)}%`;
    const twrText = analytics.performance.twrPct == null ? 'TWR needs at least two daily snapshots' : `TWR is ${analytics.performance.twrPct.toFixed(1)}%`;
    return `Return on recorded cost is ${analytics.performance.costReturnPct.toFixed(1)}%. ${xirrText}; ${twrText}. These measures are deliberately kept separate.`;
  }
  if (/currency|dollar|rupee|usd|fx/.test(query)) {
    const usd = analytics.allocation.currency.find((row) => row.label === 'USD');
    return `USD-denominated assets are ${num(usd?.weight).toFixed(1)}% of current value. Their INR outcome combines the asset return with USD/INR movement; the desk keeps both components separate in attribution.`;
  }
  if (/today|changed|news|event/.test(query)) {
    const relevant = events.slice(0, 3);
    return relevant.length ? `The latest portfolio-linked items are: ${relevant.map((event) => `${event.symbol || 'Portfolio'}: ${event.title}`).join('; ')}. Their presence is factual; investment impact still requires analyst judgment.` : 'No portfolio-linked event is available from the current feeds.';
  }
  return `The portfolio has ${analytics.positions.length} positions, ${analytics.dataQuality.priceCoveragePct.toFixed(0)}% observed price coverage, ${analytics.concentration.toLowerCase()} concentration, and ${analytics.performance.observations} aligned return observations. Ask a narrower question for a calculation-backed explanation.`;
}
