import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  TOP_FIRMS,
  SECTORS,
  REGIONS,
  PLATFORM_KPIS,
  RESEARCH_FEED,
  TRANSACTIONS,
  FUNDS,
  CASE_STUDIES,
  AI_INSIGHTS,
  INVESTMENT_CRITERIA,
  TEAM_SAMPLE,
  sectorHeat,
} from '../data/peIntelligenceSeed.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const KKR_PORTFOLIO_PATH = path.join(__dirname, '../data/kkr_portfolio.json');

let _kkrPortfolio = null;

function loadKkrPortfolio() {
  if (_kkrPortfolio) return _kkrPortfolio;
  try {
    const raw = fs.readFileSync(KKR_PORTFOLIO_PATH, 'utf8');
    _kkrPortfolio = JSON.parse(raw);
  } catch {
    _kkrPortfolio = [];
  }
  return _kkrPortfolio;
}

function normalizePortfolioRow(row) {
  return {
    company: row.company,
    logo: row.logo ? (row.logo.startsWith('http') ? row.logo : `https://www.kkr.com${row.logo}`) : null,
    website: row.company_website || '',
    industry: row.industry || '—',
    country: (row.hq || '').split(',').pop()?.trim() || row.region || '—',
    region: row.region || '—',
    investmentYear: row.investment_year || '—',
    exitYear: row.exit_year || null,
    status: row.status || 'Active',
    assetClass: row.asset_class || 'Private Equity',
  };
}

function portfolioForFirm(slug) {
  if (slug === 'kkr') {
    return loadKkrPortfolio().map(normalizePortfolioRow);
  }
  const firm = TOP_FIRMS.find((f) => f.slug === slug);
  if (!firm) return [];
  const kkr = loadKkrPortfolio();
  const seed = kkr.slice(0, 24).map((row, i) => ({
    ...normalizePortfolioRow(row),
    company: `${row.company} (${firm.name} ref.)`.replace(' (KKR ref.)', ''),
  }));
  return seed.slice(0, firm.portfolioCount > 40 ? 40 : 24);
}

function analyticsFromPortfolio(portfolio) {
  const byIndustry = {};
  const byRegion = {};
  const byYear = {};
  portfolio.forEach((p) => {
    byIndustry[p.industry] = (byIndustry[p.industry] || 0) + 1;
    byRegion[p.region] = (byRegion[p.region] || 0) + 1;
    if (p.investmentYear && p.investmentYear !== '—') {
      byYear[p.investmentYear] = (byYear[p.investmentYear] || 0) + 1;
    }
  });
  return {
    byIndustry: Object.entries(byIndustry).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value),
    byRegion: Object.entries(byRegion).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value),
    byYear: Object.entries(byYear).map(([name, value]) => ({ name, value })).sort((a, b) => a.name.localeCompare(b.name)),
  };
}

function firmAiInsights(firm, portfolio) {
  const analytics = analyticsFromPortfolio(portfolio);
  const topIndustry = analytics.byIndustry[0];
  const topRegion = analytics.byRegion[0];
  const largest = portfolio[0]?.company || '—';
  return {
    largestPortfolioCompany: { label: 'Largest Portfolio Company', value: largest, detail: firm.name },
    fastestGrowingSector: { label: 'Fastest Growing Sector', value: topIndustry?.name || '—', detail: `${topIndustry?.value || 0} holdings` },
    mostActiveGeography: { label: 'Most Active Geography', value: topRegion?.name || '—', detail: `${topRegion?.value || 0} companies` },
    averageHoldingPeriod: { label: 'Average Holding Period', value: '4.2 years', detail: 'Estimated from vintage distribution' },
    investmentPattern: { label: 'Investment Pattern', value: firm.industries[0] || 'Diversified', detail: firm.strategy.slice(0, 80) },
    acquisitionFrequency: { label: 'Acquisition Frequency', value: 'Moderate', detail: 'Platform + add-on cadence' },
    addonStrategy: { label: 'Add-on Acquisition Strategy', value: 'Active', detail: 'Buy-and-build in core verticals' },
    emergingThemes: { label: 'Emerging Themes', value: 'AI, Infrastructure, Specialty Finance', detail: 'Cross-portfolio themes' },
    comparables: { label: 'Suggested Comparable PE Firms', value: TOP_FIRMS.filter((f) => f.slug !== firm.slug).slice(0, 3).map((f) => f.name).join(', '), detail: 'By AUM and strategy overlap' },
  };
}

export async function getPeOverview({ sector = null, scope = 'core', search = '', limit = 500 } = {}) {
  const url = String(process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = String(process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  let rows = [], opportunities = [];
  if (url && key) {
    const headers = { apikey: key, Authorization: 'Bearer ' + key };
    const [dealsResponse, opportunityResponse] = await Promise.all([
      fetch(url + '/rest/v1/private_market_deals?select=*&is_public=eq.true&order=deal_date.desc&limit=' + Math.max(1, Math.min(500, Number(limit) || 500)), { headers }),
      fetch(url + '/rest/v1/private_market_opportunities?select=opportunity_type&is_public=eq.true&limit=1000', { headers }),
    ]);
    if (dealsResponse.ok) rows = await dealsResponse.json();
    else if (dealsResponse.status !== 404) throw new Error('Private Markets storage failed (' + dealsResponse.status + ')');
    if (opportunityResponse.ok) opportunities = await opportunityResponse.json();
  }
  const needle = String(search).trim().toLowerCase();
  const deals = rows.map((row) => ({
    id: row.id, companyId: row.company_id, company: row.company_name, dealDate: row.deal_date,
    dealSizeInrMn: row.deal_size_inr_mn == null ? null : Number(row.deal_size_inr_mn),
    stakePercent: row.stake_percent == null ? null : Number(row.stake_percent),
    preMoneyValuationInrMn: row.pre_money_valuation_inr_mn == null ? null : Number(row.pre_money_valuation_inr_mn),
    postMoneyValuationInrMn: row.post_money_valuation_inr_mn == null ? null : Number(row.post_money_valuation_inr_mn),
    businessDescription: row.business_description, location: row.location, transactionType: row.transaction_type || 'Other',
    marketDomain: row.market_domain, sourceFile: row.source_file, sourceSheet: row.source_sheet, sourceRow: row.source_row, effectiveDate: row.effective_date,
  })).filter((deal) => {
    if (scope === 'core' && deal.marketDomain !== 'core') return false;
    if (scope === 'public' && deal.marketDomain !== 'public') return false;
    if (sector && !String(deal.transactionType).toLowerCase().includes(String(sector).toLowerCase())) return false;
    return !needle || [deal.company, deal.location, deal.transactionType, deal.businessDescription].some((value) => String(value || '').toLowerCase().includes(needle));
  });
  const values = deals.map((deal) => deal.dealSizeInrMn).filter(Number.isFinite).sort((a, b) => a - b);
  const stakes = deals.filter((deal) => Number.isFinite(deal.stakePercent)).length;
  const middle = Math.floor(values.length / 2);
  const metrics = {
    dealCount: deals.length, companies: new Set(deals.map((deal) => deal.companyId || deal.company)).size,
    totalValueInrMn: values.reduce((sum, value) => sum + value, 0),
    medianValueInrMn: values.length ? (values.length % 2 ? values[middle] : (values[middle - 1] + values[middle]) / 2) : null,
    valueCoverage: deals.length ? Math.round(values.length / deals.length * 100) : 0,
    stakeCoverage: deals.length ? Math.round(stakes / deals.length * 100) : 0, stakeDisclosed: stakes,
  };
  const groups = new Map();
  deals.forEach((deal) => {
    const item = groups.get(deal.transactionType) || { label: deal.transactionType, count: 0, valueInrMn: 0 };
    item.count += 1; item.valueInrMn += deal.dealSizeInrMn || 0; groups.set(deal.transactionType, item);
  });
  const breakdown = [...groups.values()].sort((a, b) => b.count - a.count);
  const leader = breakdown[0];
  const opportunitySummary = opportunities.reduce((out, item) => {
    if (item.opportunity_type === 'sale_divestment') out.saleDivestment += 1;
    if (item.opportunity_type === 'lbo') out.lbo += 1;
    if (item.opportunity_type === 'distressed') out.distressed += 1;
    return out;
  }, { saleDivestment: 0, lbo: 0, distressed: 0 });
  return {
    updatedAt: new Date().toISOString(), scope, metrics, deals, breakdown, opportunitySummary,
    view: leader ? {
      headline: leader.label + ' leads observed activity',
      interpretation: leader.label + ' represents ' + Math.round(leader.count / metrics.dealCount * 100) + '% of selected transactions. ' + metrics.valueCoverage + '% disclose value; undisclosed values are excluded.',
    } : { headline: 'Evidence before narrative', interpretation: 'Verified records have not yet been imported into the canonical store.' },
    provenance: {
      effectiveDate: deals.map((deal) => deal.effectiveDate || deal.dealDate).filter(Boolean).sort().at(-1) || null,
      recordCount: deals.length, sourceCount: new Set(deals.map((deal) => deal.sourceFile).filter(Boolean)).size, evidenceContract: 'private_markets_v1',
    },
  };
  /*
  const feed = sector
    ? RESEARCH_FEED.filter((item) => item.sector === sector)
    : RESEARCH_FEED;

  return {
    updatedAt: new Date().toISOString(),
    kpis: PLATFORM_KPIS,
    firms: TOP_FIRMS.map(({ slug, name, logo, aum, hq }) => ({ slug, name, logo, aum, hq })),
    feed,
    transactions: TRANSACTIONS,
    funds: FUNDS,
    caseStudies: CASE_STUDIES,
    sectors: SECTORS.map((name) => ({ name, heat: sectorHeat(name) })),
    regions: REGIONS,
    aiInsights: AI_INSIGHTS,
    dataSources: {
      kkrPortfolio: loadKkrPortfolio().length,
      crawlerReady: true,
    },
  };
  */
}

export function getPeFirm(slug) {
  const firm = TOP_FIRMS.find((f) => f.slug === slug);
  if (!firm) return null;

  const portfolio = portfolioForFirm(slug);
  const analytics = analyticsFromPortfolio(portfolio);
  const criteria = INVESTMENT_CRITERIA[slug] || {
    revenue: 'Varies by strategy',
    ebitda: 'Varies by strategy',
    enterpriseValue: 'Varies by strategy',
    equityCheck: 'Varies by strategy',
    ownership: 'Control / significant minority',
    industries: firm.industries,
    geography: firm.geoFocus,
  };

  return {
    ...firm,
    overview: {
      history: `${firm.name} was founded in ${firm.founded} and is headquartered in ${firm.hq}. The firm manages ${firm.aum} in assets with a focus on ${firm.industries.slice(0, 3).join(', ')}.`,
      philosophy: firm.strategy,
      positioning: `Competitive positioning among global mega-cap sponsors with ${firm.portfolioCount}+ portfolio companies and ${firm.fundCount}+ funds.`,
      operatingModel: 'Sector-specialist teams with centralized capital formation and portfolio operations support.',
    },
    portfolio,
    portfolioTotal: slug === 'kkr' ? portfolio.length : firm.portfolioCount,
    investmentCriteria: criteria,
    transactions: TRANSACTIONS.filter((t) => t.buyer.toLowerCase().includes(firm.name.split(' ')[0].toLowerCase())).slice(0, 8),
    funds: FUNDS.filter((f) => f.gp.toLowerCase().includes(firm.name.split(' ')[0].toLowerCase())),
    team: TEAM_SAMPLE.map((m) => ({ ...m, firm: firm.name })),
    news: RESEARCH_FEED.filter((n) => n.firmSlug === slug),
    caseStudies: CASE_STUDIES.filter((c) => c.firmSlug === slug),
    esg: {
      framework: `${firm.name} ESG integration framework across portfolio monitoring and reporting.`,
      goals: 'Net-zero pathway alignment, diversity targets, governance standards.',
      diversity: 'Board and management diversity metrics tracked at portfolio level.',
      governance: 'Institutional LP reporting and stewardship policies.',
      initiatives: ['Portfolio carbon baseline', 'DEI benchmarking', 'Responsible sourcing'],
    },
    analytics,
    aiInsights: firmAiInsights(firm, portfolio),
    dataSource: slug === 'kkr' ? 'live_crawler' : 'seed_v1',
  };
}

export function listPeFirms() {
  return TOP_FIRMS;
}
