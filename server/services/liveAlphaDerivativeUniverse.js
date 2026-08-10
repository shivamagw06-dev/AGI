import { resolveUpstoxAccessToken } from '../providers/upstox.js';

const SEARCH_URL = process.env.UPSTOX_INSTRUMENT_SEARCH_URL || 'https://api.upstox.com/v2/instruments/search';

async function resolveOne(member, { fetchFn, token }) {
  if (member.derivativeInstrumentKey) return { ...member, derivativeResolution: 'configured' };
  const params = new URLSearchParams({
    query: member.symbol,
    exchanges: 'NSE',
    segments: 'FO',
    instrument_types: 'FUT',
    expiry: 'current_month',
    page_number: '1',
    records: '10',
  });
  const response = await fetchFn(`${SEARCH_URL}?${params}`, {
    headers: { Accept: 'application/json', Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(10_000),
  });
  if (!response.ok) throw new Error(`instrument search ${response.status}`);
  const payload = await response.json();
  const matches = (payload?.data || []).filter((row) => (
    row.segment === 'NSE_FO'
    && row.instrument_type === 'FUT'
    && row.underlying_key === member.instrumentKey
    && String(row.instrument_key || '').startsWith('NSE_FO|')
  ));
  matches.sort((left, right) => String(left.expiry || '').localeCompare(String(right.expiry || '')));
  const nearest = matches[0];
  return nearest
    ? { ...member, derivativeInstrumentKey: nearest.instrument_key, derivativeResolution: 'upstox_current_month', derivativeExpiry: nearest.expiry || null }
    : { ...member, derivativeResolution: 'not_found' };
}

export async function resolveLiveAlphaDerivatives(universe, { fetchFn = globalThis.fetch } = {}) {
  const enabled = String(process.env.LIVE_ALPHA_DERIVATIVE_AUTO_RESOLVE || 'true').toLowerCase() !== 'false';
  const configured = universe.members.filter((row) => row.derivativeInstrumentKey).length;
  if (!enabled || configured === universe.members.length) {
    return { ...universe, derivativeResolution: { status: enabled ? 'configured' : 'disabled', configured, resolved: 0, missing: universe.members.length - configured, errors: [] } };
  }
  const { token } = resolveUpstoxAccessToken();
  if (!token || typeof fetchFn !== 'function') {
    return { ...universe, derivativeResolution: { status: 'unavailable', configured, resolved: 0, missing: universe.members.length - configured, errors: ['upstox_access_token_unavailable'] } };
  }
  const members = [];
  const errors = [];
  // Keep concurrency modest: this runs once at boot and should not create an
  // API burst or compete with the live market feed authorization.
  for (let index = 0; index < universe.members.length; index += 4) {
    const group = universe.members.slice(index, index + 4);
    const settled = await Promise.allSettled(group.map((member) => resolveOne(member, { fetchFn, token })));
    settled.forEach((result, offset) => {
      const original = group[offset];
      if (result.status === 'fulfilled') members.push(result.value);
      else {
        members.push({ ...original, derivativeResolution: 'error' });
        errors.push({ symbol: original.symbol, error: result.reason?.message || 'instrument_search_failed' });
      }
    });
  }
  const resolved = members.filter((row) => row.derivativeInstrumentKey && row.derivativeResolution === 'upstox_current_month').length;
  const totalConfigured = members.filter((row) => row.derivativeInstrumentKey).length;
  return {
    ...universe,
    members,
    derivativeResolution: {
      status: totalConfigured >= 10 ? 'ready' : 'insufficient',
      configured,
      resolved,
      missing: members.length - totalConfigured,
      errors,
    },
  };
}
