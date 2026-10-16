export const GROWTH_MOMENTUM_ID = 'in-growth-momentum-private';
export function growthMomentumPortfolio(portfolios) {
  const parents = ['in-growth', 'in-momentum'].map(id => portfolios.find(p => p.id === id));
  if (parents.some(p => !p || p.incomplete || !p.holdings?.length)) throw Error('Complete Growth and Momentum allocations are required.');
  const holdings = new Map();
  let cashWeight = 0;
  for (const p of parents) {
    const total = p.holdings.reduce((sum,h) => sum + h.weight, Number(p.cashWeight || 0));
    if (!Number.isFinite(total) || Math.abs(total - 100) > 0.05) throw Error('Source weights must total 100%.');
    const seen = new Set();
    for (const h of p.holdings) {
      if (!h.symbol || seen.has(h.symbol) || !Number.isFinite(h.weight) || h.weight <= 0) throw Error('Invalid source holding.');
      seen.add(h.symbol);
      const old = holdings.get(h.symbol);
      if (old?.instrumentKey && h.instrumentKey && old.instrumentKey !== h.instrumentKey) throw Error('Conflicting instrument identities.');
      const weight = h.weight / total * 50;
      holdings.set(h.symbol, {...h, instrumentKey: old?.instrumentKey || h.instrumentKey, weight: (old?.weight || 0) + weight,
        contributions: [...(old?.contributions || []), {portfolioId:p.id, name:p.name, weight}]});
    }
    cashWeight += Number(p.cashWeight || 0) / total * 50;
  }
  return {id:GROWTH_MOMENTUM_ID, name:'Growth + Momentum', market:'india', category:'Private research', visibility:'admin',
    asOf:parents.map(p=>p.asOf).sort().at(-1), revision:parents.map(p=>`${p.id}:${p.revision || 0}`).join('|'),
    description:'50% Growth + 50% Momentum. Existing source weights are retained within each half; overlapping stocks are combined. Private forward-tracking experiment.',
    weightMethod:'Each source portfolio receives 50%. Source weights are normalized only for rounding tolerance (maximum 0.05 percentage points). Shared stock contributions are added. Launch units are frozen; no automatic rebalancing.',
    sources:parents.map(p=>({id:p.id,name:p.name,revision:p.revision,asOf:p.asOf,stockCount:p.holdings.length})),
    incomplete:false,cashWeight,holdings:[...holdings.values()].sort((a,b)=>b.weight-a.weight || a.symbol.localeCompare(b.symbol))};
}
export function withGrowthMomentum(portfolios) {
  const publicRows = portfolios.filter(p=>p.id!==GROWTH_MOMENTUM_ID && p.visibility!=='admin');
  return [...publicRows,growthMomentumPortfolio(publicRows)];
}
