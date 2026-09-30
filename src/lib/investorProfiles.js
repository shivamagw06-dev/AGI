export function investorSlug(name) {
  const normalized = String(name).normalize('NFKC').trim().toLowerCase();
  let hash = 2166136261;
  for (const character of normalized) hash = Math.imul(hash ^ character.codePointAt(0), 16777619);
  return `${normalized.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'investor'}-${(hash >>> 0).toString(16)}`;
}

export function investorPath(country, name) {
  return `/institutions/${country.toLowerCase()}/${investorSlug(name)}`;
}

export function numberFromDisclosure(value) {
  if (value == null || !/^[+-]?[\d,.]+%?$/.test(String(value).trim())) return null;
  const number = Number(String(value).replaceAll(',', '').replace('%', ''));
  return Number.isFinite(number) ? number : null;
}

export function disclosureStatus(row) {
  const change = String(row.change || '').toLowerCase();
  if (change.includes('below')) return 'Below threshold';
  if (change === 'new' || change === 'buy') return 'New disclosure';
  if (change.startsWith('add ')) return 'Increased';
  if (change.startsWith('reduce ')) return 'Reduced';
  const delta = numberFromDisclosure(change);
  if (delta > 0) return 'Increased';
  if (delta < 0) return 'Reduced';
  if ((row.quantity == null || row.quantity === '-') && (!row.history?.[0] || row.history[0] === '-')) return 'Historical / unavailable';
  return delta === 0 ? 'Unchanged' : 'Disclosed';
}

export function portfolioCsv(profile) {
  const escape = value => {
    let text = String(value ?? '');
    // Prevent spreadsheet formulas in imported names while preserving numeric signs.
    if (/^[=+@\t\r]/.test(text) || (/^-/.test(text) && numberFromDisclosure(text) == null)) text = `'${text}`;
    return `"${text.replaceAll('"', '""')}"`;
  };
  const header = ['Stock', 'Holder', 'Security class / option / units', 'CUSIP', 'Holding value (reported units)', 'Quantity', 'Reported change', ...profile.periods, 'Reporting period', 'Retrieved'];
  return [header, ...profile.rows.map(row => [row.stock, row.holder, row.security, row.cusip, row.value, row.quantity, row.change, ...profile.periods.map((_, i) => row.history?.[i] ?? ''), row.reportPeriod || profile.reportPeriod, profile.retrievedAt])].map(row => row.map(escape).join(',')).join('\r\n');
}
