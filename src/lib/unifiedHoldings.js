// Keep provenance in the underlying records; present one company list without
// adding potentially overlapping family or legal-holder positions together.
const key = value => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
export function unifiedHoldings(profile, disclosures, mappings = {}) {
  if (!profile) return [];
  const rows = (profile.rows || []).map((row, snapshotIndex) => ({ ...row, snapshotIndex, disclosures: [] }));
  for (const filing of disclosures) {
    const matches = rows.filter(row => key(row.stock) === key(filing.stock) || (mappings[row.stock]?.symbol?.replace(/\.(NS|BO)$/, '') === filing.symbol));
    if (matches.length === 1) { matches[0].disclosures.push(filing); if (matches[0].filingIdentity) { matches[0].quantity = 'See holder details'; matches[0].holder = ''; } continue; }
    // Ambiguous security classes cannot safely be merged by issuer alone.
    const existing = rows.find(row => row.filingIdentity === (filing.isin || filing.symbol));
    if (existing) { existing.disclosures.push(filing); existing.quantity = 'See holder details'; existing.history = []; continue; }
    rows.push({ stock: filing.stock, holder: filing.holder, value: '—', quantity: filing.quantity.toLocaleString('en-IN'), change: '—', history: [], reportPeriod: filing.period, filingIdentity: filing.isin || filing.symbol, disclosures: [filing] });
  }
  return rows;
}
