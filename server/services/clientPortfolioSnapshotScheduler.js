import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';
import { getPortfolioMarketPackage } from './portfolioMarketService.js';

const IST_ZONE = 'Asia/Kolkata';
const RUN_AFTER_MINUTE = (18 * 60) + 15;
const CHECK_INTERVAL_MS = 10 * 60 * 1000;

let timer = null;
let running = false;
let lastRunDate = null;
let lastResult = null;

function istParts(date = new Date()) {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: IST_ZONE,
    weekday: 'short',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date).reduce((accumulator, part) => ({ ...accumulator, [part.type]: part.value }), {});
  return {
    date: `${parts.year}-${parts.month}-${parts.day}`,
    weekday: parts.weekday,
    minuteOfDay: (Number(parts.hour) * 60) + Number(parts.minute),
  };
}

function valueForHolding(holding, marketPackage) {
  const market = marketPackage?.instruments?.[holding.id] || {};
  const price = Number(market.price ?? holding.current_price ?? holding.average_cost ?? 0);
  const fx = holding.currency === 'USD'
    ? Number(marketPackage?.fx?.usdInr?.price ?? holding.fx_rate_to_inr ?? 1)
    : 1;
  const quantity = Number(holding.quantity || 0);
  const cost = Number(holding.average_cost || 0);
  return {
    value: quantity * price * fx,
    invested: quantity * cost * fx,
    cash: holding.asset_type === 'cash' ? quantity * price * fx : 0,
    observed: ['live', 'observed'].includes(market.quality),
  };
}

async function snapshotPortfolio(supabase, portfolio, runDate) {
  const [{ data: holdings, error: holdingsError }, { data: transactions, error: transactionsError }, { data: previous, error: previousError }] = await Promise.all([
    supabase.from('client_portfolio_holdings').select('*').eq('portfolio_id', portfolio.id),
    supabase.from('client_portfolio_transactions').select('external_flow_base').eq('portfolio_id', portfolio.id).eq('trade_date', runDate),
    supabase.from('client_portfolio_snapshots').select('total_value_inr').eq('portfolio_id', portfolio.id).lt('snapshot_date', runDate).order('snapshot_date', { ascending: false }).limit(1).maybeSingle(),
  ]);
  if (holdingsError) throw holdingsError;
  if (transactionsError) throw transactionsError;
  if (previousError) throw previousError;
  if (!holdings?.length) return { portfolioId: portfolio.id, status: 'empty' };

  const marketPackage = await getPortfolioMarketPackage({ instruments: holdings, days: 750 });
  const values = holdings.map((holding) => valueForHolding(holding, marketPackage));
  const totalValue = values.reduce((sum, row) => sum + row.value, 0);
  const investedValue = values.reduce((sum, row) => sum + row.invested, 0);
  const cashValue = values.reduce((sum, row) => sum + row.cash, 0);
  const externalFlow = (transactions || []).reduce((sum, row) => sum + Number(row.external_flow_base || 0), 0);
  const previousValue = Number(previous?.total_value_inr || 0);
  const dailyReturn = previousValue > 0 ? (((totalValue - externalFlow) / previousValue) - 1) * 100 : null;
  const observed = values.filter((row) => row.observed).length;
  const dataQuality = {
    grade: observed === holdings.length ? 'A' : observed >= holdings.length * 0.8 ? 'B' : 'C',
    priceCoveragePct: holdings.length ? (observed / holdings.length) * 100 : 0,
    generatedAt: marketPackage.generatedAt,
    source: 'after_market_scheduler',
  };

  const { error } = await supabase.from('client_portfolio_snapshots').upsert({
    portfolio_id: portfolio.id,
    user_id: portfolio.user_id,
    snapshot_date: runDate,
    total_value_inr: totalValue,
    invested_value_inr: investedValue,
    cash_value_inr: cashValue,
    net_external_flow_inr: externalFlow,
    daily_return_pct: dailyReturn,
    analytics: { coverage: marketPackage.coverage, automated: true },
    data_quality: dataQuality,
  }, { onConflict: 'portfolio_id,snapshot_date' });
  if (error) throw error;
  return { portfolioId: portfolio.id, status: 'saved', holdings: holdings.length, totalValue, observed };
}

export async function runClientPortfolioSnapshots({ force = false } = {}) {
  const clock = istParts();
  if (!force && (['Sat', 'Sun'].includes(clock.weekday) || clock.minuteOfDay < RUN_AFTER_MINUTE || lastRunDate === clock.date)) {
    return { ok: true, skipped: true, date: clock.date, reason: 'outside_window_or_already_complete' };
  }
  if (running) return { ok: true, skipped: true, date: clock.date, reason: 'already_running' };
  const supabase = createSupabaseAdmin();
  if (!supabase) return { ok: false, skipped: true, date: clock.date, reason: 'supabase_admin_unavailable' };

  running = true;
  try {
    const { data: portfolios, error } = await supabase.from('client_portfolios').select('id,user_id,name,base_currency');
    if (error) throw error;
    const results = [];
    for (const portfolio of portfolios || []) {
      try { results.push(await snapshotPortfolio(supabase, portfolio, clock.date)); }
      catch (error) { results.push({ portfolioId: portfolio.id, status: 'failed', error: error.message }); }
    }
    const failed = results.filter((row) => row.status === 'failed').length;
    lastResult = { ok: failed === 0, date: clock.date, portfolios: results.length, failed, results, completedAt: new Date().toISOString() };
    if (failed === 0) lastRunDate = clock.date;
    return lastResult;
  } finally {
    running = false;
  }
}

export function startClientPortfolioSnapshotScheduler() {
  if (timer) return;
  const check = () => runClientPortfolioSnapshots().catch((error) => {
    lastResult = { ok: false, error: error.message, completedAt: new Date().toISOString() };
    console.warn('[portfolio-snapshots] run failed:', error.message);
  });
  timer = setInterval(check, CHECK_INTERVAL_MS);
  timer.unref?.();
  void check();
}

export function getClientPortfolioSnapshotStatus() {
  return { running, lastRunDate, lastResult, timezone: IST_ZONE, scheduledAfter: '18:15' };
}
