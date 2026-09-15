function apiBase() {
  if (typeof window !== 'undefined' && window.API_URL) return String(window.API_URL).replace(/\/$/, '');
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
}

async function request(path) {
  const response = await fetch(`${apiBase()}/api/ipo${path}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || 'Unable to load IPO information.');
  }
  return response.json();
}

export function getIpoSummary() {
  return request('/summary');
}

function asPlatform(payload = {}) {
  const active = payload.active || [];
  const upcoming = payload.upcoming || [];
  const closed = payload.closed || [];
  const listed = payload.listed || [];
  const calendar = payload.calendar || [];
  return {
    active,
    upcoming,
    closed,
    listed,
    calendar,
    counts: payload.counts || {
      active: active.length,
      upcoming: upcoming.length,
      closed: closed.length,
      listed: listed.length,
    },
    source: payload.source,
    updatedAt: payload.updatedAt,
    nextRefreshAt: payload.nextRefreshAt,
    unavailable: payload.unavailable,
    disclaimer: payload.disclaimer,
  };
}

/** Prefers /platform; soft-falls back to /summary while Render catches up. */
export async function getIpoPlatform() {
  try {
    return asPlatform(await request('/platform'));
  } catch {
    const summary = await request('/summary');
    return asPlatform({
      ...summary,
      closed: summary.closed || [],
      listed: summary.listed || [],
      calendar: [],
    });
  }
}

export function getIpoDetail(symbol) {
  return request(`/${encodeURIComponent(symbol)}`);
}
