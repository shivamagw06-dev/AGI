const MONTHS = {
  jan: 0, feb: 1, mar: 2, apr: 3, may: 4, jun: 5,
  jul: 6, aug: 7, sep: 8, oct: 9, nov: 10, dec: 11,
};

function cleanText(value = '') {
  return String(value)
    .replace(/\r/g, '')
    .replace(/\u00a0/g, ' ')
    .replace(/[–—]/g, '-')
    .replace(/[ \t]+$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function numberFrom(value) {
  if (value == null || value === '') return null;
  const normalized = String(value).replace(/[^0-9.-]/g, '');
  if (!normalized || normalized === '-' || normalized === '.' || normalized === '-.') return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function firstMatch(text, patterns) {
  for (const pattern of patterns) {
    const match = text.match(pattern);
    if (match?.[1] != null) return String(match[1]).trim();
  }
  return null;
}

function isoDate(value) {
  if (!value) return null;
  const match = String(value).trim().match(/(?:\w{3},\s*)?([A-Za-z]{3,9})\s+(\d{1,2}),\s*(\d{4})/);
  if (!match) return null;
  const month = MONTHS[match[1].slice(0, 3).toLowerCase()];
  if (month == null) return null;
  return new Date(Date.UTC(Number(match[3]), month, Number(match[2]))).toISOString().slice(0, 10);
}

function sectionBetween(text, startPattern, endPattern) {
  const start = text.match(startPattern);
  if (!start || start.index == null) return '';
  const tail = text.slice(start.index + start[0].length);
  const end = tail.match(endPattern);
  return (end?.index == null ? tail : tail.slice(0, end.index)).trim();
}

function lines(value = '') {
  return value
    .split('\n')
    .map((line) => line.replace(/^[#*\-\s]+/, '').trim())
    .filter((line) => line && line.length > 8 && !/^updated on\b/i.test(line));
}

function parseThreePeriodRows(text) {
  const periodLine = firstMatch(text, [/Period Ended\s+([^\n]+)/i]);
  const periods = periodLine
    ? [...periodLine.matchAll(/(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})/g)].map((match) => match[1])
    : [];
  const names = [
    ['assets', 'Assets'],
    ['total_income', 'Total Income'],
    ['profit_after_tax', 'Profit After Tax'],
    ['ebitda', 'EBITDA'],
    ['net_worth', 'NET Worth'],
    ['reserves_and_surplus', 'Reserves and Surplus'],
    ['total_borrowing', 'Total Borrowing'],
  ];
  const rows = {};
  for (const [key, label] of names) {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = text.match(new RegExp(`(?:^|\\n)${escaped}\\s+([0-9.,-]+)\\s+([0-9.,-]+)\\s+([0-9.,-]+)`, 'i'));
    if (match) rows[key] = match.slice(1, 4).map(numberFrom);
  }
  return { periods, rows };
}

function parseKpis(text) {
  const block = sectionBetween(text, /Key Performance Indicator \(KPI\)/i, /Check IPO Peer Comparison|IPO Valuation/i);
  const labels = ['ROE', 'ROCE', 'Debt/Equity', 'RoNW', 'PAT Margin', 'EBITDA Margin', 'NAV', 'Price to Book Value'];
  return Object.fromEntries(labels.flatMap((label) => {
    const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const match = block.match(new RegExp(`(?:^|\\n)${escaped}[ \\t]+([^\\s\\n]+)(?:[ \\t]+([^\\s\\n]+))?`, 'i'));
    return match ? [[label, [numberFrom(match[1]), numberFrom(match[2])]]] : [];
  }));
}

function normalizeName(value = '') {
  return String(value)
    .toLowerCase()
    .replace(/\b(initial public offering|public issue|ipo|limited|ltd|company|co)\b/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim();
}

function valuesConflict(left, right, tolerance = 0.02) {
  const a = numberFrom(left);
  const b = numberFrom(right);
  if (a == null || b == null) return false;
  return Math.abs(a - b) > Math.max(0.01, Math.abs(b) * tolerance);
}

export function matchPastedIpoToUpstox(parsed, platform = {}) {
  const records = ['active', 'upcoming', 'closed', 'listed'].flatMap((key) => platform?.[key] || []);
  const target = normalizeName(parsed?.companyName);
  if (!target) return null;
  return records
    .map((record) => {
      const candidate = normalizeName(record.name);
      const exact = candidate === target;
      const overlap = target.split(' ').filter((token) => token.length > 3 && candidate.includes(token)).length;
      return { record, score: exact ? 100 : overlap };
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)[0]?.record || null;
}

export function comparePastedWithUpstox(parsed, record) {
  if (!record) return [];
  const checks = [
    ['Issue size', parsed.issue.issueSizeCr, record.issueSize, 'crore'],
    ['Minimum price', parsed.issue.priceMin, record.minPrice, 'INR'],
    ['Maximum price', parsed.issue.priceMax, record.maxPrice, 'INR'],
    ['Lot size', parsed.application.lotSize, record.lotSize, 'shares'],
  ];
  const conflicts = checks.flatMap(([label, pasted, upstox, unit]) => (
    valuesConflict(pasted, upstox)
      ? [{ label, pasted, upstox, unit }]
      : []
  ));
  const dateChecks = [
    ['IPO open', parsed.timeline.open, record.biddingStartDate],
    ['IPO close', parsed.timeline.close, record.biddingEndDate],
    ['Allotment', parsed.timeline.allotment, record.allotmentDate],
    ['Listing', parsed.timeline.listing, record.listingDate],
  ];
  for (const [label, pasted, upstox] of dateChecks) {
    if (pasted && upstox && pasted !== upstox) conflicts.push({ label, pasted, upstox, unit: 'date' });
  }
  return conflicts;
}

export function parseIpoPaste(rawText, { sourceUrl = '', sourceName = 'Chittorgarh' } = {}) {
  const text = cleanText(rawText);
  if (text.length < 120) throw new Error('Paste the complete IPO detail text before extracting.');

  const narrativeName = firstMatch(text, [/^(.+?) IPO is\s+/i]);
  const aboutName = firstMatch(text, [/About\s+(.+?)(?:\n|Updated on)/i]);
  const companyName = (aboutName || narrativeName || '').replace(/\s+/g, ' ').trim();
  if (!companyName) throw new Error('Company name could not be identified from the pasted IPO text.');

  const issueSizeCr = numberFrom(firstMatch(text, [
    /IPO is (?:a|an) .*? issue of\s*₹\s*([\d,.]+)\s*crores?/i,
    /Total Issue Size[\s\S]{0,90}?agg\. up to\s*₹\s*([\d,.]+)\s*Cr/i,
  ]));
  const totalIssueShares = numberFrom(firstMatch(text, [/Total Issue Size\s*([\d,]+)\s*shares/i]));
  const freshIssueShares = numberFrom(firstMatch(text, [/Fresh Issue(?:\s*\(Ex Market Maker\))?\s*([\d,]+)\s*shares/i]));
  const freshIssueAmountCr = numberFrom(firstMatch(text, [
    /fresh issue of[\s\S]{0,80}?aggregating to\s*₹\s*([\d,.]+)\s*crores?/i,
    /Fresh Issue(?:\s*\(Ex Market Maker\))?[\s\S]{0,100}?agg\. up to\s*₹\s*([\d,.]+)\s*Cr/i,
  ]));
  const offerForSaleShares = numberFrom(firstMatch(text, [/Offer for Sale\s*([\d,]+)\s*shares/i]));
  const offerForSaleAmountCr = numberFrom(firstMatch(text, [
    /offer for sale of[\s\S]{0,80}?aggregating to\s*₹\s*([\d,.]+)\s*crores?/i,
    /Offer for Sale[\s\S]{0,100}?agg\. up to\s*₹\s*([\d,.]+)\s*Cr/i,
  ]));
  const marketMakerShares = numberFrom(firstMatch(text, [/Reserved for Market Maker\s*([\d,]+)\s*shares/i]));
  const price = text.match(/Price Band\s*₹?\s*([\d,]+)\s*(?:to|-)\s*₹?\s*([\d,]+)/i)
    || text.match(/price band (?:set )?(?:between|at)?\s*₹?\s*([\d,]+)\s*(?:to|and|-)\s*₹?\s*([\d,]+)/i);
  const priceMin = numberFrom(price?.[1]);
  const priceMax = numberFrom(price?.[2]);

  const openDate = isoDate(firstMatch(text, [/bidding opened[^\n]*? on\s+([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i, /IPO Open\s+(?:\w{3},\s*)?([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i]));
  const closeDate = isoDate(firstMatch(text, [/will close on\s+([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i, /IPO Close\s+(?:\w{3},\s*)?([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i]));
  const allotmentDate = isoDate(firstMatch(text, [/allotment[^\n]*?(?:on|as)\s+([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i, /Allotment\s+(?:\w{3},\s*)?([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i]));
  const refundDate = isoDate(firstMatch(text, [/Refund\s+(?:\w{3},\s*)?([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i]));
  const listingDate = isoDate(firstMatch(text, [/listing date (?:fixed as|is)\s+([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i, /Listing\s+(?:\w{3},\s*)?([A-Za-z]{3,9}\s+\d{1,2},\s*\d{4})/i]));

  const retailRow = text.match(/(?:Individual investors? \(IND\)|Retail) \(Min\)\s+(\d+)\s+([\d,]+)\s+₹\s*([\d,]+)/i);
  const hniRow = text.match(/S-HNI \(Min\)\s+(\d+)\s+([\d,]+)\s+₹\s*([\d,]+)/i);
  const lotSize = numberFrom(firstMatch(text, [/Lot Size\s*([\d,]+)\s*Shares/i, /lot size for an application is\s*([\d,]+)\s*shares/i]));
  const financials = parseThreePeriodRows(text);
  const kpis = parseKpis(text);
  const valuationBlock = sectionBetween(text, /IPO Valuation/i, /Shareholding Structure/i);
  const peRow = valuationBlock.match(/P\/E \(x\)[ \t]+([-\d,.]+)(?:[ \t]+([-\d,.]+))?/i);
  const epsRow = valuationBlock.match(/EPS \(₹\)[ \t]+([-\d,.]+)(?:[ \t]+([-\d,.]+))?/i);
  const marketCapRow = valuationBlock.match(/Market Cap at Offer Price[ \t]+(?:₹\s*)?([-\d,.]+)(?:\s*Cr\.?)?[ \t]+(?:₹\s*)?([-\d,.]+)(?:\s*Cr\.?)?/i);
  const epsPre = numberFrom(epsRow?.[1]);
  const epsPost = numberFrom(epsRow?.[2]);
  const pePre = numberFrom(peRow?.[1]);
  const pePost = numberFrom(peRow?.[2]);
  const marketCapPreCr = numberFrom(marketCapRow?.[1]);
  const marketCapPostCr = numberFrom(marketCapRow?.[2]);
  const revenueGrowth = numberFrom(firstMatch(text, [/revenue increased by\s*([\d.]+)%/i]));
  const patGrowth = numberFrom(firstMatch(text, [/profit after tax \(PAT\) rose by\s*([\d.]+)%/i]));

  const about = sectionBetween(text, /About\s+.+?(?:\n|Updated on[^\n]*\n)/i, /Competitive Strengths|Company Financials/i)
    .replace(/^Updated on[^\n]*\n?/i, '')
    .trim();
  const explicitStrengths = lines(sectionBetween(text, /Competitive Strengths/i, /Company Financials/i));
  const objectiveBlock = sectionBetween(text, /IPO Objects of the Issue/i, /Key Performance Indicator/i);
  const objectives = [...objectiveBlock.matchAll(/(?:^|\n)(\d+)\s+([^\n]+?)(?:\s+([\d,.]+))?(?=\n|$)/g)]
    .map((match) => ({ order: Number(match[1]), description: match[2].trim(), amountCr: numberFrom(match[3]) }))
    .filter((item) => item.description.length > 8 && !/^Issue Objects/i.test(item.description));

  const latestDebtEquity = kpis['Debt/Equity']?.[0] ?? null;
  const priorDebtEquity = kpis['Debt/Equity']?.[1] ?? null;
  const latestBorrowing = financials.rows.total_borrowing?.[0] ?? null;
  const priorBorrowing = financials.rows.total_borrowing?.[1] ?? null;
  const debtRepaymentObjectiveCr = objectives
    .filter((item) => /repayment|pre-payment|prepayment|borrowings|lenders/i.test(item.description))
    .reduce((total, item) => total + (item.amountCr || 0), 0);
  const debtRepaymentShare = freshIssueAmountCr && debtRepaymentObjectiveCr
    ? debtRepaymentObjectiveCr / freshIssueAmountCr
    : null;
  const exportShare = numberFrom(firstMatch(text, [/export-focused business contributed\s*([\d.]+)%/i]));
  const isSme = /NSE SME|BSE SME|SME IPO/i.test(text);
  const completedProjects = numberFrom(firstMatch(about, [/completed more than\s*([\d,]+)\s*projects/i]));
  const latestRoce = kpis.ROCE?.[0] ?? null;
  const promoterPrePct = numberFrom(firstMatch(text, [/Promoter and Promoter Group\s*([\d.]+)%/i]));
  const promoterPostPct = numberFrom(firstMatch(text, [/Promoter and Promoter Group\s*[\d.]+%\s*([\d.]+)%/i]));
  const marginNow = kpis['EBITDA Margin']?.[0] ?? null;
  const marginPrior = kpis['EBITDA Margin']?.[1] ?? null;
  const strengths = [...explicitStrengths];
  if (!strengths.length) {
    if (revenueGrowth != null && patGrowth != null) strengths.push(`Reported revenue growth of ${revenueGrowth}% and PAT growth of ${patGrowth}% in FY2026.`);
    if (latestDebtEquity != null && latestDebtEquity <= 0.5) strengths.push(`Low reported leverage, with debt/equity of ${latestDebtEquity.toFixed(2)}x in FY2026.`);
    if (latestRoce != null && latestRoce >= 20) strengths.push(`Strong reported capital efficiency, with ROCE of ${latestRoce}% in FY2026.`);
    if (completedProjects != null) strengths.push(`Execution track record of more than ${completedProjects} completed projects as of the reported date.`);
    if (/international markets/i.test(about)) strengths.push('Operations span India and international markets, providing geographic diversification.');
  }
  const risks = [];
  if (exportShare != null) risks.push(`Export concentration is high at ${exportShare}% of revenue, increasing geographic, currency and external-demand sensitivity.`);
  if (latestDebtEquity != null && latestDebtEquity >= 1) risks.push(`Leverage remains meaningful with debt/equity of ${latestDebtEquity.toFixed(2)}x despite the reported improvement.`);
  if (latestBorrowing != null && priorBorrowing != null && latestBorrowing > priorBorrowing * 1.25) {
    const debtGrowth = Math.round((latestBorrowing / priorBorrowing - 1) * 100);
    const ratioContext = latestDebtEquity != null && priorDebtEquity != null
      ? `, while debt/equity increased from ${priorDebtEquity.toFixed(2)}x to ${latestDebtEquity.toFixed(2)}x`
      : '';
    risks.push(`Total borrowings increased ${debtGrowth}% to INR ${latestBorrowing} crore from INR ${priorBorrowing} crore${ratioContext}.`);
  } else if (latestDebtEquity != null && priorDebtEquity != null && latestDebtEquity > priorDebtEquity * 1.2) {
    risks.push(`Debt/equity increased from ${priorDebtEquity.toFixed(2)}x to ${latestDebtEquity.toFixed(2)}x.`);
  }
  if (debtRepaymentShare != null && debtRepaymentShare >= 0.5) {
    risks.push(`Debt repayment absorbs about ${Math.round(debtRepaymentShare * 100)}% of fresh-issue proceeds, limiting capital available for growth investment.`);
  }
  if (/setting up a new manufacturing facility|capital expenditure/i.test(objectiveBlock)) risks.push('Execution and ramp-up risk is elevated because a material portion of proceeds funds new capacity.');
  if (offerForSaleAmountCr != null && issueSizeCr != null && offerForSaleAmountCr / issueSizeCr >= 0.5) risks.push(`The offer for sale represents ${Math.round(offerForSaleAmountCr / issueSizeCr * 100)}% of the issue, so most IPO proceeds go to selling shareholders rather than the company.`);
  if (marginNow != null && marginPrior != null && marginNow < marginPrior) risks.push(`EBITDA margin declined to ${marginNow}% from ${marginPrior}%, which warrants scrutiny of pricing, mix and execution.`);
  if (promoterPrePct != null && promoterPostPct != null && promoterPrePct - promoterPostPct >= 5) risks.push(`Promoter ownership falls from ${promoterPrePct}% to ${promoterPostPct}% after the issue.`);
  if (isSme) risks.push('SME-listed shares can have lower liquidity and higher post-listing price volatility.');
  if (!risks.length) risks.push('The pasted source did not include a dedicated risk-factor section; complete RHP risk review is still required.');

  const positiveParts = [];
  if (revenueGrowth != null) positiveParts.push(`${revenueGrowth}% revenue growth`);
  if (patGrowth != null) positiveParts.push(`${patGrowth}% PAT growth`);
  if (marginNow != null && marginPrior != null && marginNow > marginPrior) positiveParts.push(`EBITDA margin expansion to ${marginNow}% from ${marginPrior}%`);
  const thesis = `Neutral pending analyst review: ${positiveParts.join(', ') || 'reported operating momentum'} supports the opportunity, while ${risks.slice(0, 2).map((risk) => risk.replace(/\.$/, '').toLowerCase()).join(' and ')}.`;

  const businessQuality = strengths.length >= 5 ? 72 : strengths.length >= 2 ? 64 : '';
  let financialQuality = 50;
  if (revenueGrowth != null && revenueGrowth >= 20) financialQuality += 10;
  if (patGrowth != null && patGrowth >= 20) financialQuality += 10;
  if (marginNow != null && marginPrior != null && marginNow > marginPrior) financialQuality += 8;
  if (marginNow != null && marginPrior != null && marginNow < marginPrior) financialQuality -= 6;
  if (latestDebtEquity != null && latestDebtEquity > 1.5) financialQuality -= 8;
  if ((latestBorrowing != null && priorBorrowing != null && latestBorrowing > priorBorrowing * 1.25)
    || (latestDebtEquity != null && priorDebtEquity != null && latestDebtEquity > priorDebtEquity * 1.2)) financialQuality -= 8;
  const suggestedScores = {
    business_quality: businessQuality,
    financial_quality: Math.max(0, Math.min(100, financialQuality)),
    valuation: '',
    governance: '',
    issue_structure: debtRepaymentShare != null && debtRepaymentShare >= 0.75
      ? 55
      : /Fresh capital only/i.test(text) ? 75 : (offerForSaleAmountCr != null && issueSizeCr != null && offerForSaleAmountCr / issueSizeCr >= 0.75 ? 45 : 60),
    demand_quality: '',
  };

  const leadManagerBlock = sectionBetween(text, /IPO Lead Manager\(s\)/i, /Lead Manager Reports/i);
  const leadManagers = lines(leadManagerBlock).filter((name) => !/performance|tracker|reports?/i.test(name));
  const narrativeLeadManager = firstMatch(text, [/([A-Za-z .()]+) is the book running lead manager/i]);
  if (!leadManagers.length && narrativeLeadManager) leadManagers.push(narrativeLeadManager);

  const extractedSubscription = {
    total: numberFrom(firstMatch(text, [/IPO is subscribed\s*([\d.]+)\s*times/i])),
    observedAt: firstMatch(text, [/IPO is subscribed[^\n]*? on\s+([^\n]+?)(?:\s*\(Day|\.)/i]),
    qib: numberFrom(firstMatch(text, [/QIB \(Ex Anchor\)\s*([\d.]+)/i])),
    nii: numberFrom(firstMatch(text, [/(?:^|\n)NII\*?\s*([\d.]+)/i])),
    retail: numberFrom(firstMatch(text, [/Individual Investor\s*([\d.]+)/i])),
  };
  const today = new Date().toISOString().slice(0, 10);
  const subscriptionState = openDate && today < openDate
    ? 'not_open'
    : extractedSubscription.total != null ? 'pasted' : 'not_provided';
  const subscription = subscriptionState === 'not_open'
    ? { total: null, observedAt: null, qib: null, nii: null, retail: null, state: subscriptionState }
    : { ...extractedSubscription, state: subscriptionState };

  const warnings = [];
  if (Object.values(kpis).some((values) => values.some((value) => value == null))) {
    warnings.push('One or more KPI comparison periods are unavailable; missing values remain Pending and are excluded from scoring.');
  }
  const valuationValues = [epsPre, epsPost, pePre, pePost, marketCapPreCr, marketCapPostCr];
  if (valuationValues.some((value) => value != null) && valuationValues.some((value) => value == null)) {
    warnings.push('The source contains a partial valuation table; available values were preserved and missing values remain Pending.');
  }

  const fields = {
    company: Boolean(companyName), issue: issueSizeCr != null, priceBand: priceMax != null,
    timeline: Boolean(openDate && closeDate), application: lotSize != null,
    companyProfile: Boolean(about), strengths: strengths.length > 0,
    financials: Object.keys(financials.rows).length > 0, kpis: Object.keys(kpis).length > 0,
    valuation: valuationValues.some((value) => value != null), objectives: objectives.length > 0,
    registrar: /IPO Registrar/i.test(text), subscription: subscriptionState === 'not_open' || extractedSubscription.total != null,
  };
  const completeness = Math.round(Object.values(fields).filter(Boolean).length / Object.keys(fields).length * 100);

  return {
    companyName,
    issue: {
      issueSizeCr, totalIssueShares, freshIssueShares, freshIssueAmountCr,
      offerForSaleShares, offerForSaleAmountCr, marketMakerShares,
      priceMin, priceMax,
      faceValue: numberFrom(firstMatch(text, [/Face Value\s*₹\s*([\d,.]+)/i])),
      saleType: firstMatch(text, [/Sale Type\s*([^\n]+)/i]),
      issueType: firstMatch(text, [/Issue Type\s*([^\n]+)/i]),
      listingAt: firstMatch(text, [/Listing At\s*([^\n]+)/i]),
      marketCapCr: numberFrom(firstMatch(text, [/Market Cap\*?\s*₹\s*([\d,.]+)\s*Cr/i])),
    },
    application: {
      lotSize,
      retailLots: numberFrom(retailRow?.[1]), retailShares: numberFrom(retailRow?.[2]), retailAmount: numberFrom(retailRow?.[3]),
      hniLots: numberFrom(hniRow?.[1]), hniShares: numberFrom(hniRow?.[2]), hniAmount: numberFrom(hniRow?.[3]),
    },
    timeline: { open: openDate, close: closeDate, allotment: allotmentDate, refund: refundDate, listing: listingDate },
    participants: {
      registrar: firstMatch(text, [/IPO Registrar\s+([^\n]+)/i, /([A-Za-z .()]+) is the registrar of the issue/i]),
      leadManager: leadManagers.join(', ') || null,
      leadManagers,
      marketMaker: firstMatch(text, [/Market Maker of the company is\s+([^\n]+)/i]),
      promoters: firstMatch(text, [/Company Promoters:\s*([^\n]+)/i]),
    },
    company: { about, exportRevenuePct: exportShare },
    strengths,
    risks,
    financials: { ...financials, revenueGrowthPct: revenueGrowth, patGrowthPct: patGrowth },
    kpis,
    valuation: {
      epsPre, epsPost,
      pePre, pePost,
      marketCapPreCr, marketCapPostCr,
    },
    shareholding: {
      preIssueShares: numberFrom(firstMatch(text, [/Share Holding Pre Issue\s*([\d,]+)\s*shares/i])),
      postIssueShares: numberFrom(firstMatch(text, [/Share Holding Post Issue\s*([\d,]+)\s*shares/i])),
      promoterPrePct,
      promoterPostPct,
    },
    anchor: {
      amountCr: numberFrom(firstMatch(text, [/IPO raises\s*₹\s*([\d,.]+)\s*crore from anchor/i])),
      shares: numberFrom(firstMatch(text, [/Shares Offered\s*([\d,]+)/i])),
      bidDate: isoDate(firstMatch(text, [/Anchor bid date is\s+([A-Za-z]+\s+\d{1,2},\s*\d{4})/i])),
    },
    objectives,
    subscription,
    thesis,
    suggestedScores,
    warnings,
    fields,
    completeness,
    source: { name: sourceName, url: sourceUrl.trim() || null, importedAt: new Date().toISOString(), rawTextLength: text.length },
  };
}

function escapeHtml(value = '') {
  return String(value).replace(/[&<>"']/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
}

function cell(value, suffix = '') {
  return value == null || value === '' ? 'Pending' : `${value}${suffix}`;
}

function table(headers, rows) {
  return `<table><thead><tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join('')}</tr></thead><tbody>${rows.map((row) => `<tr>${row.map((value) => `<td>${escapeHtml(value)}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}

export function buildIpoKeyData(parsed, matchedIpo = null) {
  const issue = parsed.issue;
  const application = parsed.application;
  return [
    `Issue size: ${issue.issueSizeCr != null ? `INR ${issue.issueSizeCr} crore` : 'Pending'}`,
    `Price band: ${issue.priceMin != null ? `INR ${issue.priceMin} - INR ${issue.priceMax}` : 'Pending'}`,
    `Lot size: ${application.lotSize != null ? `${application.lotSize} shares` : 'Pending'}`,
    `Retail minimum: ${application.retailAmount != null ? `INR ${application.retailAmount}` : 'Pending'}`,
    `Listing: ${issue.listingAt || matchedIpo?.listingExchange || 'Pending'}`,
    `Upstox ID: ${matchedIpo?.ipoId || 'Unmatched'}`,
    `Source: ${parsed.source.name}${parsed.source.url ? ` - ${parsed.source.url}` : ''}`,
  ].join('\n');
}

export function buildIpoArticleHtml(parsed, matchedIpo = null) {
  const issue = parsed.issue;
  const app = parsed.application;
  const financialRows = Object.entries(parsed.financials.rows).map(([key, values]) => [
    key.replaceAll('_', ' ').replace(/\b\w/g, (char) => char.toUpperCase()),
    ...values.map((value) => cell(value)),
  ]);
  const kpiRows = Object.entries(parsed.kpis).map(([label, values]) => [label, ...values.map((value) => cell(value))]);
  return `
    <p><strong>Automated extraction, analyst review required.</strong> Facts below were structured from ${escapeHtml(parsed.source.name)} and cross-matched with ${matchedIpo ? 'the Upstox IPO feed' : 'no Upstox record yet'}.</p>
    ${parsed.warnings?.length ? `<p><strong>Validation notes:</strong> ${parsed.warnings.map(escapeHtml).join(' ')}</p>` : ''}
    <h2>IPO decision brief</h2>
    <p>${escapeHtml(parsed.thesis)}</p>
    <h2>Issue snapshot</h2>
    ${table(['Field', 'Value'], [
      ['Issue size', cell(issue.issueSizeCr, ' crore')],
      ['Price band', issue.priceMin != null ? `INR ${issue.priceMin} - INR ${issue.priceMax}` : 'Pending'],
      ['Face value', cell(issue.faceValue)],
      ['Issue type', cell(issue.issueType)],
      ['Sale type', cell(issue.saleType)],
      ['Fresh issue', issue.freshIssueAmountCr != null ? `INR ${issue.freshIssueAmountCr} crore (${cell(issue.freshIssueShares, ' shares')})` : cell(issue.freshIssueShares, ' shares')],
      ['Offer for sale', issue.offerForSaleAmountCr != null ? `INR ${issue.offerForSaleAmountCr} crore (${cell(issue.offerForSaleShares, ' shares')})` : cell(issue.offerForSaleShares, ' shares')],
      ['Listing venue', cell(issue.listingAt)],
      ['Lot size', cell(app.lotSize, ' shares')],
      ['Retail minimum', app.retailAmount != null ? `INR ${app.retailAmount}` : 'Pending'],
    ])}
    <h2>Timeline</h2>
    ${table(['Event', 'Date'], Object.entries(parsed.timeline).map(([label, date]) => [label.replace(/\b\w/g, (char) => char.toUpperCase()), cell(date)]))}
    <h2>Company overview</h2>
    ${parsed.company.about.split(/\n\n+/).filter(Boolean).map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join('') || '<p>Company profile requires analyst completion.</p>'}
    <h2>Potential strengths</h2>
    <ul>${parsed.strengths.map((item) => `<li>${escapeHtml(item)}</li>`).join('') || '<li>No explicit strengths were extracted.</li>'}</ul>
    <h2>Principal risks</h2>
    <ul>${parsed.risks.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>
    <h2>Financial performance</h2>
    ${financialRows.length ? table(['Metric', ...(parsed.financials.periods.length ? parsed.financials.periods : ['Latest', 'Prior', 'Earlier'])], financialRows) : '<p>Financial table was not detected.</p>'}
    <h2>Key performance indicators</h2>
    ${kpiRows.length ? table(['KPI', 'Latest', 'Prior'], kpiRows) : '<p>KPI table was not detected.</p>'}
    <h2>Valuation snapshot</h2>
    ${table(['Metric', 'Pre issue', 'Post issue'], [
      ['EPS', cell(parsed.valuation.epsPre), cell(parsed.valuation.epsPost)],
      ['P/E', cell(parsed.valuation.pePre, 'x'), cell(parsed.valuation.pePost, 'x')],
      ['Market capitalisation', cell(parsed.valuation.marketCapPreCr, ' crore'), cell(parsed.valuation.marketCapPostCr, ' crore')],
    ])}
    <h2>Objects of the issue</h2>
    <ol>${parsed.objectives.map((item) => `<li>${escapeHtml(item.description)}${item.amountCr != null ? `: INR ${item.amountCr} crore` : ''}</li>`).join('') || '<li>Use of proceeds requires RHP verification.</li>'}</ol>
    <h2>Subscription snapshot</h2>
    ${parsed.subscription.state === 'not_open' ? '<p>Not open yet. Live subscription data will appear after bidding begins.</p>' : table(['Category', 'Subscription'], [
      ['QIB', cell(parsed.subscription.qib, 'x')],
      ['NII', cell(parsed.subscription.nii, 'x')],
      ['Retail', cell(parsed.subscription.retail, 'x')],
      ['Total', cell(parsed.subscription.total, 'x')],
    ])}
    <h2>Issue participants</h2>
    ${table(['Role', 'Name'], [
      ['Lead managers', cell(parsed.participants.leadManager)],
      ['Registrar', cell(parsed.participants.registrar)],
      ['Market maker', cell(parsed.participants.marketMaker)],
      ['Promoters', cell(parsed.participants.promoters)],
    ])}
    <h2>Sources and verification</h2>
    <p>Primary live issue data: Upstox IPO API. Pasted research source: ${parsed.source.url ? `<a href="${escapeHtml(parsed.source.url)}">${escapeHtml(parsed.source.name)}</a>` : escapeHtml(parsed.source.name)}. Subscription and GMP are time-sensitive and must be refreshed before publication.</p>
  `.replace(/\n\s+/g, '\n').trim();
}
