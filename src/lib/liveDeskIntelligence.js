/**
 * Deterministic market intelligence from data AGI already holds.
 *
 * Every item traces to a number in the market snapshot or a theme from AGI's
 * own engine. Nothing here writes prose that is not backed by a figure, and
 * nothing invents a statistic - in particular there are no percentile claims,
 * because the snapshot carries no historical distribution to compute one from.
 *
 * Ranking, in order: magnitude, cross-asset confirmation, then recency. A
 * large isolated move therefore ranks below a smaller one that several assets
 * agree on, which is the way a desk actually reads a session.
 */

const CATEGORY = {
  NIFTY: 'EQUITIES', SENSEX: 'EQUITIES', 'BANK NIFTY': 'EQUITIES',
  MIDCAP: 'EQUITIES', SMALLCAP: 'EQUITIES', 'S&P': 'EQUITIES',
  NASDAQ: 'EQUITIES', Dow: 'EQUITIES',
  USDINR: 'FX',
  Brent: 'COMMODITIES', Gold: 'COMMODITIES', Silver: 'COMMODITIES',
  'INDIA VIX': 'MACRO',
  Bitcoin: 'MACRO',
};

const GEOGRAPHY = {
  NIFTY: 'INDIA', SENSEX: 'INDIA', 'BANK NIFTY': 'INDIA', MIDCAP: 'INDIA',
  SMALLCAP: 'INDIA', 'INDIA VIX': 'INDIA', USDINR: 'INDIA',
  'S&P': 'US', NASDAQ: 'US', Dow: 'US',
};

/** Move sizes that make an asset worth a line. Set per asset class because a
 *  0.5% day is nothing for Bitcoin and a lot for a currency pair. */
const THRESHOLD = {
  USDINR: 0.25,
  'INDIA VIX': 2.0,
  Gold: 0.6, Silver: 1.0, Brent: 1.0, Bitcoin: 2.0,
  default: 0.4,
};

const num = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
};

function describe(name, changePct) {
  const up = changePct > 0;
  const size = Math.abs(changePct);
  const strength = size >= 1.5 ? 'sharply' : size >= 0.75 ? 'firmly' : 'modestly';
  switch (name) {
    case 'INDIA VIX':
      return up
        ? `India VIX is ${strength} higher, indicating demand for downside protection.`
        : `India VIX is ${strength} lower, consistent with easing hedging demand.`;
    case 'USDINR':
      return up
        ? `The rupee is weaker against the dollar, which pressures importers and supports exporters.`
        : `The rupee is firmer against the dollar, easing imported cost pressure.`;
    case 'Brent':
      return up
        ? `Crude is ${strength} higher, which lifts energy producers and raises input costs elsewhere.`
        : `Crude is ${strength} lower, easing input costs for transport and industrials.`;
    case 'Gold':
      return up
        ? `Gold is ${strength} higher, a move usually associated with defensive positioning.`
        : `Gold is ${strength} lower, consistent with reduced defensive demand.`;
    default:
      return up
        ? `${name} is ${strength} higher on the session.`
        : `${name} is ${strength} lower on the session.`;
  }
}

function severityFor(changePct, confirmations) {
  const size = Math.abs(changePct);
  if (size >= 1.5 || confirmations >= 3) return 'MAJOR';
  if (size >= 0.75 || confirmations >= 2) return 'NOTABLE';
  return 'WATCH';
}

function istTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata',
  })} IST`;
}

/**
 * @param snapshot AGI market snapshot rows
 * @param themes   AGI market themes (its own engine, already ranked by confidence)
 */
export function buildIntelligence(snapshot = [], themes = []) {
  const rows = (snapshot || [])
    .map((row) => ({
      name: String(row?.name || '').trim(),
      changePct: num(row?.percentChange),
      price: num(row?.price),
      updatedAt: row?.updatedAt || null,
      stale: Boolean(row?.stale || row?.liveUnavailable),
    }))
    .filter((row) => row.name && row.changePct !== null);

  const byName = new Map(rows.map((row) => [row.name, row]));

  // Cross-asset confirmation: how many other assets moved the same way by a
  // meaningful amount. This is what separates a real session from one index
  // drifting.
  const meaningful = rows.filter((row) => Math.abs(row.changePct) >= 0.3);
  const up = meaningful.filter((row) => row.changePct > 0).length;
  const down = meaningful.filter((row) => row.changePct < 0).length;

  const items = [];
  for (const row of rows) {
    const limit = THRESHOLD[row.name] ?? THRESHOLD.default;
    if (Math.abs(row.changePct) < limit) continue;

    const sameDirection = row.changePct > 0 ? up : down;
    const confirmations = Math.max(sameDirection - 1, 0);

    const evidence = [{ label: row.name, value: row.changePct }];
    for (const peer of ['NIFTY', 'S&P', 'INDIA VIX', 'Gold', 'USDINR', 'Brent']) {
      if (peer === row.name) continue;
      const other = byName.get(peer);
      if (other && Math.abs(other.changePct) >= 0.2) {
        evidence.push({ label: peer, value: other.changePct });
      }
      if (evidence.length >= 5) break;
    }

    items.push({
      id: `mi-${row.name}`,
      category: CATEGORY[row.name] || 'MACRO',
      geography: GEOGRAPHY[row.name] || null,
      headline: `${row.name} ${row.changePct > 0 ? 'higher' : 'lower'}`,
      body: describe(row.name, row.changePct),
      changePct: row.changePct,
      severity: severityFor(row.changePct, confirmations),
      time: istTime(row.updatedAt),
      sortKey: Math.abs(row.changePct) + confirmations * 0.35,
      confirmations,
      evidence,
      sources: ['AGI Market Data'],
      stale: row.stale,
    });
  }

  // AGI's own themes carry a confidence the price feed cannot express, so they
  // are included but never outrank a live move on magnitude alone.
  for (const theme of (themes || []).slice(0, 4)) {
    const confidence = num(theme?.confidence);
    if (confidence === null || confidence < 0.6) continue;
    items.push({
      id: `theme-${theme.id || theme.name}`,
      category: 'MACRO',
      geography: 'INDIA',
      headline: `${theme.name}: ${theme.trend || 'in focus'}`,
      body: `AGI's theme engine reads ${theme.name} as ${String(theme.trend || '').toLowerCase()} with a ${theme.bias || 'neutral'} bias.`,
      severity: confidence >= 0.75 ? 'NOTABLE' : 'WATCH',
      time: null,
      sortKey: confidence,
      confirmations: 0,
      evidence: [
        { label: 'Confidence', value: `${Math.round(confidence * 100)}%` },
        ...(Array.isArray(theme.tickers) ? theme.tickers.slice(0, 3).map((t) => ({ label: t, value: 'in theme' })) : []),
      ],
      sources: ['AGI Theme Engine'],
    });
  }

  return items.sort((a, b) => b.sortKey - a.sortKey);
}

export const FILTERS = ['ALL', 'EQUITIES', 'FX', 'COMMODITIES', 'MACRO', 'INDIA', 'US'];

export function applyFilter(items, filter) {
  if (!filter || filter === 'ALL') return items;
  if (filter === 'INDIA' || filter === 'US') {
    return items.filter((item) => item.geography === filter);
  }
  return items.filter((item) => item.category === filter);
}
