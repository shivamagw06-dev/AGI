import { supabase } from '@/lib/supabaseClient';

const PORTFOLIO_ID = 'founder';

function throwIfError(error) {
  if (error) throw error;
}

export async function getFounderPortfolioPublic() {
  const [settingsResult, disclosuresResult, performanceResult, attributionResult] = await Promise.all([
    supabase
      .from('founder_portfolio_settings')
      .select('*')
      .eq('portfolio_id', PORTFOLIO_ID)
      .maybeSingle(),
    supabase
      .from('founder_portfolio_disclosures')
      .select('*')
      .eq('is_published', true)
      .order('public_weight', { ascending: false }),
    supabase
      .from('founder_portfolio_performance')
      .select('*')
      .order('snapshot_date', { ascending: true })
      .limit(400),
    supabase
      .from('founder_portfolio_attribution')
      .select('*')
      .order('valuation_date', { ascending: false })
      .limit(50),
  ]);
  throwIfError(settingsResult.error);
  throwIfError(disclosuresResult.error);
  throwIfError(performanceResult.error);
  throwIfError(attributionResult.error);
  return {
    settings: settingsResult.data || null,
    holdings: disclosuresResult.data || [],
    performance: performanceResult.data || [],
    attribution: attributionResult.data || [],
  };
}

export async function getFounderPortfolioAdmin() {
  const [settingsResult, disclosuresResult, transactionsResult, reportsResult] = await Promise.all([
    supabase
      .from('founder_portfolio_settings')
      .select('*')
      .eq('portfolio_id', PORTFOLIO_ID)
      .maybeSingle(),
    supabase
      .from('founder_portfolio_disclosures')
      .select('*')
      .order('updated_at', { ascending: false }),
    supabase
      .from('founder_portfolio_transactions')
      .select('*')
      .order('trade_date', { ascending: false })
      .limit(100),
    supabase
      .from('founder_portfolio_validation_reports')
      .select('*')
      .order('run_at', { ascending: false })
      .limit(30),
  ]);
  throwIfError(settingsResult.error);
  throwIfError(disclosuresResult.error);
  throwIfError(transactionsResult.error);
  throwIfError(reportsResult.error);
  return {
    settings: settingsResult.data || null,
    disclosures: disclosuresResult.data || [],
    transactions: transactionsResult.data || [],
    reports: reportsResult.data || [],
  };
}

export async function saveFounderPortfolioSettings(settings) {
  const payload = {
    ...settings,
    portfolio_id: PORTFOLIO_ID,
    updated_at: new Date().toISOString(),
  };
  const { data, error } = await supabase
    .from('founder_portfolio_settings')
    .upsert(payload, { onConflict: 'portfolio_id' })
    .select()
    .single();
  throwIfError(error);
  return data;
}

export async function saveFounderDisclosure(disclosure) {
  const payload = { ...disclosure, updated_at: new Date().toISOString() };
  if (!payload.id) delete payload.id;
  const { data, error } = await supabase
    .from('founder_portfolio_disclosures')
    .upsert(payload)
    .select()
    .single();
  throwIfError(error);
  return data;
}

export async function removeFounderDisclosure(id) {
  const { error } = await supabase.from('founder_portfolio_disclosures').delete().eq('id', id);
  throwIfError(error);
}

export async function addFounderTransaction(transaction) {
  const { data, error } = await supabase
    .from('founder_portfolio_transactions')
    .insert(transaction)
    .select()
    .single();
  throwIfError(error);
  return data;
}

export async function addFounderTransactions(transactions) {
  if (!Array.isArray(transactions) || transactions.length === 0) return [];
  const { data, error } = await supabase
    .from('founder_portfolio_transactions')
    .insert(transactions)
    .select();
  throwIfError(error);
  return data || [];
}
