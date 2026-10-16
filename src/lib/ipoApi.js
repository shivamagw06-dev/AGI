import { isMainboardIpo, mainboardPlatform } from './ipoScope.js';

function apiBase() {
  if (typeof window !== 'undefined' && window.API_URL) return String(window.API_URL).replace(/\/$/, '');
  return (import.meta.env.VITE_API_URL || '').replace(/\/$/, '');
}

async function request(path) {
  const response = await fetch(`${apiBase()}/api/ipo${path}`);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.error || 'Unable to load IPO information.');
    error.status = response.status;
    throw error;
  }
  return response.json();
}

export function getIpoSummary() {
  return request('/summary').then(mainboardPlatform);
}

function asPlatform(input = {}) {
  const payload = mainboardPlatform(input);
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

export async function getIpoDetail(symbol) {
  try {
    const payload = await request(`/${encodeURIComponent(symbol)}`);
    return { ...payload, ipo: isMainboardIpo(payload.ipo || {}) ? payload.ipo : null };
  } catch (error) {
    if (error.status !== 404) throw error;
    // Upcoming issues may not have a trading symbol yet. The published picker
    // already uses their provider IPO ID; resolve that exact ID from the feed.
    const platform = await getIpoPlatform();
    const key = String(symbol || '').trim().toLowerCase();
    const ipo = ['active', 'upcoming', 'closed', 'listed']
      .flatMap((category) => platform[category] || [])
      .find((item) => key && String(item.ipoId || '').toLowerCase() === key);
    if (!ipo) throw error;
    return { ipo, source: platform.source, updatedAt: platform.updatedAt,
      nextRefreshAt: platform.nextRefreshAt, unavailable: platform.unavailable,
      disclaimer: platform.disclaimer };
  }
}
