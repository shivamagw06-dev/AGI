// Overview and research services intentionally have different populations.
// Never replace a missing count with a plausible-looking default.
export function coverageCounts(data) {
  const managers = data?.managers || [];
  const count = value => Number.isInteger(value) && value >= 0 ? value : null;
  return {
    selected: Array.isArray(data?.managers) ? managers.length : count(data?.covered_managers),
    eligible: count(data?.consensus_managers),
    withFilings: Array.isArray(data?.managers) ? managers.filter(m => m.latest_filing).length : null,
  };
}

export function secPublicationDate(value) {
  if (!value || !Number.isFinite(Date.parse(value))) return 'Date unavailable';
  return new Date(value).toLocaleDateString('en-US', {
    day: 'numeric', month: 'short', year: 'numeric',
    timeZone: /^\d{4}-\d{2}-\d{2}$/.test(value) ? 'UTC' : 'America/New_York',
  });
}

export function secManagerUrl(cik) {
  return /^\d{1,10}$/.test(String(cik || ''))
    ? `https://www.sec.gov/edgar/browse/?CIK=${String(cik).replace(/^0+/, '')}&owner=exclude`
    : null;
}

export function filingStatus(fund) {
  const status = fund?.last_refresh_status;
  const quarter = fund?.latest_filing?.report_date || 'an unknown period';
  if (status === 'reports_elsewhere') return {
    label: 'Reports through another filer',
    note: fund.last_refresh_error?.startsWith('Filed a 13F-NT notice')
      ? fund.last_refresh_error
      : `A newer 13F-NT notice was collected. The ${quarter} holdings below are historical; a notice contains no holdings table.`,
  };
  if (status === 'stale') return { label: 'Historical holdings', note: `Latest collected holdings cover ${quarter}. No newer holdings report is available in this record. This does not establish a current position or why reporting stopped.` };
  if (status === 'error') return { label: 'Refresh failed', note: 'The latest source check failed. Previously collected holdings remain dated; a failed refresh does not establish that a newer filing is absent.' };
  return { label: status === 'success' ? 'Source check completed' : 'Source check pending', note: `Holdings cover ${quarter}; a completed check is not a statement of current live ownership.` };
}

export function latestFilingEvents(managers = []) {
  const seen = new Set();
  return managers.flatMap(manager => {
    const filing = manager.latest_filing;
    if (!filing?.filed_at || !Number.isFinite(Date.parse(filing.filed_at))) return [];
    const key = filing.id || `${manager.cik}:${filing.accession_number}`;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{ key, manager: manager.display_name, filing, source: filing.source_url || secManagerUrl(manager.cik) }];
  }).sort((a, b) => Date.parse(b.filing.filed_at) - Date.parse(a.filing.filed_at));
}
