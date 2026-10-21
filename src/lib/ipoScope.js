// Only explicitly classified mainboard issues belong in the IPO catalogue.
export function isMainboardIpo(ipo = {}) {
  const type = String(ipo.issueType ?? ipo.issue_type ?? '').trim().toLowerCase();
  const flags = [ipo.isSme, ipo.is_sme];
  if (flags.some(value => value === true || value === 1 || value === 'true') || type.includes('sme')) return false;
  return ['regular', 'mainboard', 'main_board', 'main board'].includes(type)
    || flags.some(value => value === false || value === 0 || value === 'false');
}

export function mainboardPlatform(payload = {}) {
  const groups = Object.fromEntries(['active', 'upcoming', 'closed', 'listed'].map(key => [key, (payload[key] || []).filter(isMainboardIpo)]));
  return {
    ...payload, ...groups,
    calendar: (payload.calendar || []).filter(isMainboardIpo),
    counts: Object.fromEntries(Object.entries(groups).map(([key, rows]) => [key, rows.length])),
  };
}
