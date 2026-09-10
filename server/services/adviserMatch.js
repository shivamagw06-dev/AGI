/**
 * Match a tracked manager to its Form ADV registration.
 *
 * Exact on the canonical name or nothing. The adviser search index matches
 * loosely - asking it for "bridgewater" returns OIA LTD first, because
 * BRIDGEWATER appears somewhere in that firm's list of other names - so the
 * search is used to narrow and this decides.
 *
 * Two firms answering to one name is a refusal rather than a choice. A wrong
 * link here does not fail loudly: it puts another firm's registration date,
 * address and disclosure flag on a manager's profile, where it reads as fact.
 *
 * Other names are deliberately not matched on. They include predecessors,
 * relying advisers and the principals' own names, and matching them is how
 * BRIDGEWATER, JAMES becomes Bridgewater Associates.
 */
import { canonicalName } from './registrantNames.js';

/**
 * @param {string} managerName the display name we track
 * @param {{firm_name: string, firm_source_id: string}[]} hits search results
 * @returns {{firm: object, matchedBy: string} | null}
 */
export function matchAdviser(managerName, hits) {
  const want = canonicalName(managerName);
  if (!want) return null;

  const exact = new Map();
  for (const hit of hits || []) {
    if (!hit?.firm_source_id) continue;
    if (canonicalName(hit.firm_name) !== want) continue;
    exact.set(String(hit.firm_source_id), hit);
  }
  if (exact.size !== 1) return null;
  return { firm: [...exact.values()][0], matchedBy: 'legal name' };
}

/** The office address, which the API returns as JSON inside a string. */
export function officeAddress(firm) {
  const raw = firm?.firm_ia_address_details;
  if (!raw) return { city: null, country: null };
  try {
    const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
    const office = parsed?.officeAddress || parsed || {};
    return { city: office.city || null, country: office.country || null };
  } catch {
    // The field is a string of JSON and nothing guarantees it parses. An
    // address is the least of what this table carries.
    return { city: null, country: null };
  }
}

/** A US date as filed, MM/DD/YYYY, to an ISO date. */
export function advDate(value) {
  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(String(value || '').trim());
  if (!match) return null;
  const [, month, day, year] = match;
  const iso = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
  return Number.isNaN(Date.parse(iso)) ? null : iso;
}
