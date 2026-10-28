// Source precision is retained. A rounded tie is not a confirmed unchanged holding.
export const researchKey = value => String(value || '').toLowerCase().replace(/[^a-z0-9]/g, '');
export function percentage(value) {
  const s = String(value ?? '').trim();
  if (!/^\d+(?:\.\d+)?%$/.test(s)) return null;
  const digits = s.split('.')[1]?.replace('%', '').length || 0;
  return { value: Number(s.slice(0, -1)), error: 0.5 * 10 ** -digits };
}
export function entityType(name, category = 'individual') {
  if (/\bgroup\b|associates|family|sons|president of india|premji|damani|hinduja|lohia/i.test(name)) return 'Group / related entities';
  if (/insurance|life assurance/i.test(name)) return 'Insurer';
  if (/fund|trust|asset management|capital|investments|wealth|llp|partners|pension/i.test(name)) return 'Fund / investment entity';
  return category === 'institutional' ? 'Institution / corporate entity' : 'Investor / identity needs review';
}
export function periodKey(value) {
  const s=String(value || '').trim();
  const iso=s.match(/^(\d{4})-(\d{2})(?:-\d{2})?$/);
  if(iso)return `${iso[1]}-${iso[2]}`;
  const text=s.match(/(?:\d{1,2}\s+)?([A-Za-z]{3,9})\s+(\d{4})/);
  const months=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec'];
  if(text&&months.includes(text[1].slice(0,3).toLowerCase()))return `${text[2]}-${String(months.indexOf(text[1].slice(0,3).toLowerCase())+1).padStart(2,'0')}`;
  const q=s.match(/^Q([1-4]) (\d{4})$/);
  return q?`${q[2]}-${String(Number(q[1])*3).padStart(2,'0')}`:null;
}
export function ownershipComparison(profile, row) {
  if (profile.kind !== 'india-disclosures') return { status: 'Source-reported share change', comparable: false };
  if (!periodKey(profile.reportPeriod) || periodKey(row.reportPeriod || profile.reportPeriod) !== periodKey(profile.reportPeriod)) return { status: 'Historical / awaiting disclosure', comparable: false };
  const latest = percentage(row.history?.[0]), prior = percentage(row.history?.[1]);
  if (!latest) return { status: 'Current ownership unavailable', comparable: false };
  if (!prior) return { status: 'Newly disclosed / prior unavailable', comparable: false };
  const delta = latest.value - prior.value, uncertainty = latest.error + prior.error;
  const status = delta > uncertainty + 1e-8 ? 'Reported stake increased' : delta < -uncertainty - 1e-8 ? 'Reported stake reduced' : 'Within source rounding';
  return { status, comparable: true, latest: latest.value, prior: prior.value, delta, uncertainty,
    grouped: entityType(profile.name).startsWith('Group'), period: profile.reportPeriod, priorPeriod: profile.periods?.[1]?.replace(/\s*%$/, '') };
}
export function holdingCoverage(profile, rows = profile?.rows || []) {
  const current = [], historical = [];
  for (const row of rows) {
    const available = profile?.kind === 'india-disclosures' ? !!percentage(row.history?.[0]) : /\d/.test(String(row.quantity ?? ''));
    (available && periodKey(profile?.reportPeriod) && periodKey(row.reportPeriod || profile?.reportPeriod) === periodKey(profile?.reportPeriod) ? current : historical).push(row);
  }
  return { current, historical, total: rows.length };
}
export function snapshotMatches(data, country, category) {
  return data?.country === country && (data.category || 'individual') === category && data.published === true && Array.isArray(data.rows);
}
