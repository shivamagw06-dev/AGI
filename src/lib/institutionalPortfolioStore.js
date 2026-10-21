import { supabase } from './supabaseClient';

function throwIf(error, label) {
  if (error) throw new Error(`${label}: ${error.message}`);
}

export async function loadInstitutionalPortfolioContext(portfolioId = null) {
  const { data: userData, error: userError } = await supabase.auth.getUser();
  throwIf(userError, 'Authentication unavailable');
  if (!userData?.user?.id) throw new Error('Sign in to load Portfolio Intelligence.');

  let portfolioQuery = supabase.from('client_portfolios').select('*');
  if (portfolioId) portfolioQuery = portfolioQuery.eq('id', portfolioId);
  const { data: portfolios, error: portfolioError } = await portfolioQuery
    .order('updated_at', { ascending: false })
    .limit(1);
  throwIf(portfolioError, 'Portfolio unavailable');
  const portfolio = portfolios?.[0];
  if (!portfolio) throw new Error('Create a portfolio before running institutional analytics.');

  const [holdingsResult, transactionsResult, snapshotsResult, policyResult] = await Promise.all([
    supabase.from('client_portfolio_holdings').select('*').eq('portfolio_id', portfolio.id),
    supabase.from('client_portfolio_transactions').select('*').eq('portfolio_id', portfolio.id).order('trade_date', { ascending: true }),
    supabase.from('client_portfolio_snapshots').select('*').eq('portfolio_id', portfolio.id).order('snapshot_date', { ascending: true }),
    supabase.from('client_portfolio_policies').select('*').eq('portfolio_id', portfolio.id).maybeSingle(),
  ]);
  throwIf(holdingsResult.error, 'Holdings unavailable');
  throwIf(transactionsResult.error, 'Transaction ledger unavailable');
  throwIf(snapshotsResult.error, 'Portfolio history unavailable');
  throwIf(policyResult.error, 'Portfolio policy unavailable');

  const holdings = holdingsResult.data || [];
  const instrumentIds = [...new Set(holdings.map((row) => row.instrument_id).filter(Boolean))];
  let fundConstituents = [];
  let constituentInstruments = [];
  let corporateActions = [];

  if (instrumentIds.length) {
    const [fundResult, actionResult] = await Promise.all([
      supabase.from('portfolio_fund_constituents').select('*').in('fund_instrument_id', instrumentIds),
      supabase.from('portfolio_corporate_actions').select('*').in('instrument_id', instrumentIds).order('ex_date', { ascending: false }),
    ]);
    throwIf(fundResult.error, 'Fund holdings evidence unavailable');
    throwIf(actionResult.error, 'Corporate-action evidence unavailable');
    fundConstituents = fundResult.data || [];
    corporateActions = actionResult.data || [];
    const constituentIds = [...new Set(fundConstituents.map((row) => row.constituent_instrument_id).filter(Boolean))];
    if (constituentIds.length) {
      const constituentResult = await supabase.from('portfolio_instruments').select('*').in('id', constituentIds);
      throwIf(constituentResult.error, 'Constituent identity unavailable');
      constituentInstruments = constituentResult.data || [];
    }
  }

  return {
    portfolio,
    holdings,
    transactions: transactionsResult.data || [],
    snapshots: snapshotsResult.data || [],
    policy: policyResult.data || null,
    fundConstituents,
    constituentInstruments,
    corporateActions,
  };
}

export async function persistInstitutionalPortfolioReport(portfolioId, report) {
  const alerts = (report.alerts || []).map((alert) => ({
    alert_key: alert.alertKey,
    severity: alert.severity,
    title: alert.title,
    detail: alert.detail,
    evidence: alert.evidence || {},
  }));
  const { error } = await supabase.rpc('sync_client_portfolio_institutional_report', {
    p_portfolio_id: portfolioId,
    p_engine_version: report.engineVersion,
    p_report: report,
    p_alerts: alerts,
  });
  throwIf(error, 'Portfolio report could not be stored');
}

