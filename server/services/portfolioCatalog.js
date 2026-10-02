import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

export function validatePortfolio(input) {
  const text = (v, max) => typeof v === 'string' ? v.trim().slice(0, max) : '';
  const name = text(input?.name, 120);
  if (!name || !['india', 'usa'].includes(input?.market)) throw new Error('Name and market are required.');
  const asOf = text(input.asOf, 10);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(asOf) || !Number.isFinite(Date.parse(asOf)) || new Date(asOf).toISOString().slice(0, 10) !== asOf) throw new Error('Enter a valid allocation date.');
  if (!Array.isArray(input.holdings) || !input.holdings.length || input.holdings.length > 100) throw new Error('Add between 1 and 100 holdings.');
  const seen = new Set();
  const holdings = input.holdings.map(h => {
    const name = text(h.name, 160), symbol = text(h.symbol, 40).toUpperCase();
    const weight = typeof h.weight === 'number' ? h.weight : Number(h.weight);
    if (!name || !Number.isFinite(weight) || weight <= 0 || weight > 100) throw new Error('Each holding needs a name and a weight greater than 0 and at most 100.');
    const key = name.toLowerCase();
    if (seen.has(key) || (symbol && seen.has(`symbol:${symbol}`))) throw new Error('Duplicate holdings are not allowed.');
    seen.add(key); if (symbol) seen.add(`symbol:${symbol}`);
    return { name, symbol, weight: Math.round(weight * 100) / 100 };
  });
  const cashWeight = Number(input.cashWeight ?? 0);
  if (!Number.isFinite(cashWeight) || cashWeight < 0 || cashWeight >= 100) throw new Error('Cash weight must be between 0 and 100%.');
  const total = holdings.reduce((a,h) => a + h.weight, 0) + cashWeight;
  const incomplete = input.incomplete === true;
  if (total > 100.05 || (!incomplete && Math.abs(total - 100) > 0.05)) throw new Error('Weights must total 100% (±0.05% rounding), or mark the allocation incomplete.');
  return { name, market: input.market, category: text(input.category, 60) || 'Custom', description: text(input.description, 2000), asOf, holdings, incomplete, cashWeight };
}

export const publicDocument = row => ({ ...row.document, id: row.id, revision: row.revision, updatedAt: row.updated_at });
export function createPortfolioStore(client = createSupabaseAdmin()) {
  const db = () => { if (!client) throw new Error('Portfolio storage unavailable'); return client.from('agi_portfolio_catalog'); };
  return {
    async list() { const { data, error } = await db().select('id,document,revision,updated_at').order('id'); if (error) throw error; return data.map(publicDocument); },
    async save(id, input, actorId) {
      const clean = validatePortfolio(input);
      if (id.startsWith('in-')) {
        const {data:tracking,error}=await client.from('agi_india_portfolio_tracking').select('portfolio_id').eq('portfolio_id',id).maybeSingle();
        if(error)throw error;
        if(tracking){const e=new Error('This allocation is tracking. A dated rebalance is required; editing the launch holdings would rewrite its record.');e.status=409;throw e;}
      }
      const { data: old, error: readError } = await db().select('document,revision').eq('id', id).maybeSingle();
      if (readError) throw readError;
      if ((old?.revision || 0) !== input.revision) { const e = new Error('This portfolio changed. Reload before editing again.'); e.status = 409; throw e; }
      const document = { ...old?.document, ...clean, sourceName: old?.document.sourceName || null, sourceUrl: old?.document.sourceUrl || null, sourceAsOf: old?.document.sourceAsOf || old?.document.asOf || null, customized: true };
      const revision = (old?.revision || 0) + 1;
      const row = { id, document, revision, updated_by: actorId, updated_at: new Date().toISOString() };
      const query = old ? db().update(row).eq('id', id).eq('revision', old.revision) : db().insert(row);
      const { data, error } = await query.select('id,document,revision,updated_at').maybeSingle();
      if (error?.code === '23505' || (!error && !data)) { const e = new Error('Another edit was saved. Reload before trying again.'); e.status = 409; throw e; }
      if (error) throw error;
      return publicDocument(data);
    },
  };
}
