import { supabase } from '@/lib/supabaseClient';

function throwIfError(error) {
  if (error) throw error;
}

async function findPortfolio() {
  const result = await supabase
    .from('client_portfolios')
    .select('*')
    .maybeSingle();
  throwIfError(result.error);
  return result.data || null;
}

export async function getOrCreateClientPortfolio() {
  let portfolio = await findPortfolio();
  if (!portfolio) {
    const created = await supabase
      .from('client_portfolios')
      .insert({ name: 'My Portfolio', base_currency: 'INR' })
      .select()
      .single();

    if (created.error?.code === '23505') portfolio = await findPortfolio();
    else {
      throwIfError(created.error);
      portfolio = created.data;
    }
  }

  const holdingsResult = await supabase
    .from('client_portfolio_holdings')
    .select('*')
    .eq('portfolio_id', portfolio.id)
    .order('asset_type')
    .order('asset_name');
  throwIfError(holdingsResult.error);

  const [transactionsResult, snapshotsResult, scenariosResult, eventsResult] = await Promise.all([
    supabase.from('client_portfolio_transactions').select('*').eq('portfolio_id', portfolio.id).order('trade_date', { ascending: false }).order('created_at', { ascending: false }),
    supabase.from('client_portfolio_snapshots').select('*').eq('portfolio_id', portfolio.id).order('snapshot_date'),
    supabase.from('client_portfolio_scenarios').select('*').eq('portfolio_id', portfolio.id).order('updated_at', { ascending: false }),
    supabase.from('client_portfolio_intelligence_events').select('*').eq('portfolio_id', portfolio.id).order('occurred_at', { ascending: false }).limit(100),
  ]);
  [transactionsResult, snapshotsResult, scenariosResult, eventsResult].forEach((result) => throwIfError(result.error));

  return {
    portfolio,
    holdings: holdingsResult.data || [],
    transactions: transactionsResult.data || [],
    snapshots: snapshotsResult.data || [],
    scenarios: scenariosResult.data || [],
    events: eventsResult.data || [],
  };
}

export async function saveClientHolding(portfolioId, holding) {
  const payload = {
    ...holding,
    portfolio_id: portfolioId,
    symbol: holding.symbol.trim().toUpperCase(),
    asset_name: holding.asset_name.trim(),
    market: holding.market?.trim().toUpperCase() || '',
    sector: holding.sector?.trim() || null,
    notes: holding.notes?.trim() || null,
    quantity: Number(holding.quantity),
    average_cost: Number(holding.average_cost),
    current_price:
      holding.current_price === '' || holding.current_price == null
        ? null
        : Number(holding.current_price),
    fx_rate_to_inr: holding.currency === 'USD' ? Number(holding.fx_rate_to_inr) : 1,
    updated_at: new Date().toISOString(),
  };

  const result = await supabase
    .from('client_portfolio_holdings')
    .upsert(payload, { onConflict: 'portfolio_id,symbol,asset_type,market' })
    .select()
    .single();
  throwIfError(result.error);
  return result.data;
}

export async function deleteClientHolding(id) {
  const result = await supabase.from('client_portfolio_holdings').delete().eq('id', id);
  throwIfError(result.error);
}

export async function recordClientTransaction(portfolioId, transaction) {
  const payload = {
    p_portfolio_id: portfolioId,
    p_trade_date: transaction.trade_date,
    p_action: transaction.action,
    p_symbol: transaction.symbol.trim().toUpperCase(),
    p_asset_name: transaction.asset_name.trim(),
    p_asset_type: transaction.asset_type,
    p_market: transaction.market?.trim().toUpperCase() || '',
    p_currency: transaction.currency,
    p_quantity: Number(transaction.quantity || 0),
    p_price: Number(transaction.price || 0),
    p_amount: transaction.amount === '' || transaction.amount == null ? null : Number(transaction.amount),
    p_fees: Number(transaction.fees || 0),
    p_fx_rate_to_inr: transaction.currency === 'USD' ? Number(transaction.fx_rate_to_inr) : 1,
    p_country: transaction.country?.trim() || null,
    p_sector: transaction.sector?.trim() || null,
    p_notes: transaction.notes?.trim() || null,
  };
  const result = await supabase.rpc('record_client_portfolio_transaction', payload);
  throwIfError(result.error);
  return result.data;
}

export async function savePortfolioSnapshot(portfolioId, snapshot, positions = []) {
  const day = new Date().toISOString().slice(0, 10);
  const snapshotResult = await supabase.from('client_portfolio_snapshots').upsert({
    portfolio_id: portfolioId,
    snapshot_date: day,
    total_value_inr: snapshot.totalValue,
    invested_value_inr: snapshot.investedValue,
    cash_value_inr: snapshot.cashValue || 0,
    net_external_flow_inr: snapshot.externalFlow || 0,
    daily_return_pct: snapshot.dailyReturn,
    portfolio_index: snapshot.portfolioIndex,
    benchmark_index: snapshot.benchmarkIndex,
    twr_pct: snapshot.twr,
    xirr_pct: snapshot.xirr,
    analytics: snapshot.analytics || {},
    data_quality: snapshot.dataQuality || {},
    updated_at: new Date().toISOString(),
  }, { onConflict: 'portfolio_id,snapshot_date' }).select().single();
  throwIfError(snapshotResult.error);

  if (positions.length) {
    const positionResult = await supabase.from('client_portfolio_position_snapshots').upsert(
      positions.map((position) => ({
        portfolio_id: portfolioId,
        snapshot_date: day,
        holding_id: position.id,
        instrument_id: position.instrument_id || null,
        symbol: position.symbol,
        quantity: position.quantity,
        price: position.effectivePrice,
        currency: position.currency,
        fx_rate_to_inr: position.effectiveFx,
        market_value_inr: position.currentValue,
        weight_pct: position.weightPct,
        price_source: position.priceSource,
        price_as_of: position.priceAsOf,
      })),
      { onConflict: 'portfolio_id,snapshot_date,symbol,holding_id' }
    );
    throwIfError(positionResult.error);
  }
  return snapshotResult.data;
}

export async function savePortfolioScenario(portfolioId, scenario) {
  const result = await supabase.from('client_portfolio_scenarios').upsert({
    id: scenario.id || undefined,
    portfolio_id: portfolioId,
    name: scenario.name,
    assumptions: scenario.assumptions,
    result: scenario.result,
    updated_at: new Date().toISOString(),
  }).select().single();
  throwIfError(result.error);
  return result.data;
}

export async function updateClientPortfolio(portfolioId, changes) {
  const result = await supabase.from('client_portfolios').update({
    ...changes,
    updated_at: new Date().toISOString(),
  }).eq('id', portfolioId).select().single();
  throwIfError(result.error);
  return result.data;
}
