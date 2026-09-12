const CACHE_MS = 30 * 60 * 1000;
const SUMMARY_LIMIT = 20;
let currentRunCache = { value: null, expiresAt: 0 };
let summaryCache = { value: null, expiresAt: 0 };

function config() {
  const url = (process.env.SUPABASE_URL || '').trim().replace(/\/$/, '');
  const key = (process.env.SUPABASE_SERVICE_ROLE_KEY || '').trim();
  if (!url || !key) {
    const error = new Error('Nifty 500 research is not configured on this server.');
    error.code = 'RESEARCH_NOT_CONFIGURED';
    throw error;
  }
  return { url, key };
}

function queryString(params) {
  return new URLSearchParams(Object.entries(params).filter(([, value]) => value !== undefined && value !== null)).toString();
}

async function supabaseSelect(table, params) {
  const { url, key } = config();
  const response = await fetch(`${url}/rest/v1/${table}?${queryString(params)}`, {
    headers: {
      apikey: key,
      Authorization: `Bearer ${key}`,
      Accept: 'application/json',
    },
  });
  if (!response.ok) {
    throw new Error(`Supabase research query failed (${response.status}): ${(await response.text()).slice(0, 300)}`);
  }
  return response.json();
}

function publicRun(run) {
  if (!run) return null;
  return {
    id: run.id,
    generatedAt: run.generated_at,
    publishedAt: run.published_at,
    runName: run.run_name,
    totalStocksAnalyzed: run.total_stocks_analyzed,
    disclaimer: run.disclaimer,
  };
}

function publicRecord(record) {
  if (!record) return null;
  return {
    symbol: record.symbol,
    overallSentiment: record.overall_sentiment,
    agiResearchScore: Number(record.agi_research_score),
    aiConfidencePercent: record.ai_confidence_percent,
    researchSummary: record.research_summary,
    trendAnalysis: record.trend_analysis,
    momentumAnalysis: record.momentum_analysis,
    volumeAnalysis: record.volume_analysis,
    volatilityAnalysis: record.volatility_analysis,
    marketStructureAnalysis: record.market_structure_analysis,
    relativeStrengthAnalysis: record.relative_strength_analysis,
    supportingFactors: record.supporting_factors || [],
    riskFactors: record.risk_factors || [],
    keyObservations: record.key_observations || [],
    lastUpdated: record.last_updated,
  };
}

export async function getCurrentResearchRun() {
  if (currentRunCache.value && currentRunCache.expiresAt > Date.now()) return currentRunCache.value;
  const rows = await supabaseSelect('nifty500_research_runs', {
    select: 'id,generated_at,published_at,run_name,total_stocks_analyzed,disclaimer',
    status: 'eq.published',
    is_current: 'eq.true',
    limit: '1',
  });
  const run = publicRun(rows[0]);
  currentRunCache = { value: run, expiresAt: Date.now() + CACHE_MS };
  return run;
}

export async function getResearchSummary() {
  if (summaryCache.value && summaryCache.expiresAt > Date.now()) return summaryCache.value;
  const run = await getCurrentResearchRun();
  if (!run) return null;

  const select = 'symbol,overall_sentiment,agi_research_score,ai_confidence_percent,last_updated';
  const [bullish, bearish, neutral] = await Promise.all([
    supabaseSelect('nifty500_stock_research', { select, run_id: `eq.${run.id}`, order: 'agi_research_score.desc', limit: String(SUMMARY_LIMIT) }),
    supabaseSelect('nifty500_stock_research', { select, run_id: `eq.${run.id}`, order: 'agi_research_score.asc', limit: String(SUMMARY_LIMIT) }),
    supabaseSelect('nifty500_stock_research', { select, run_id: `eq.${run.id}`, overall_sentiment: 'eq.Neutral', order: 'agi_research_score.desc', limit: String(SUMMARY_LIMIT) }),
  ]);
  const data = {
    run,
    topBullish: bullish.map(publicRecord),
    topBearish: bearish.map(publicRecord),
    neutralWatchlist: neutral.map(publicRecord),
  };
  summaryCache = { value: data, expiresAt: Date.now() + CACHE_MS };
  return data;
}

export async function searchResearchSymbols(rawQuery) {
  const query = String(rawQuery || '').trim().toUpperCase().replace(/[^A-Z0-9&-]/g, '');
  const run = await getCurrentResearchRun();
  if (!run) return { run: null, items: [] };
  if (!query) return { run, items: [] };

  const rows = await supabaseSelect('nifty500_stock_research', {
    select: 'symbol,overall_sentiment,agi_research_score,ai_confidence_percent,last_updated',
    run_id: `eq.${run.id}`,
    symbol: `ilike.*${query}*`,
    order: 'agi_research_score.desc',
    limit: '12',
  });
  return { run, items: rows.map(publicRecord) };
}

export async function getStockResearch(rawSymbol) {
  const symbol = String(rawSymbol || '').trim().toUpperCase().replace(/[^A-Z0-9&-]/g, '');
  const run = await getCurrentResearchRun();
  if (!run || !symbol) return { run, research: null };
  const rows = await supabaseSelect('nifty500_stock_research', {
    select: '*',
    run_id: `eq.${run.id}`,
    symbol: `eq.${symbol}`,
    limit: '1',
  });
  return { run, research: publicRecord(rows[0]) };
}

export function clearNifty500ResearchCache() {
  currentRunCache = { value: null, expiresAt: 0 };
  summaryCache = { value: null, expiresAt: 0 };
}
