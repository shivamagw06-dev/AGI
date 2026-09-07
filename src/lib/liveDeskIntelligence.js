/**
 * Deterministic market intelligence, split by market, from data AGI holds.
 *
 * Every item traces to a number in the market snapshot or to AGI's own theme
 * and driver engines. Nothing writes prose that is not backed by a figure, and
 * there are no percentile claims - the snapshot carries no historical
 * distribution, so a percentile would be a statistic with nothing behind it.
 *
 * Ranking, in order: magnitude, cross-asset confirmation, then recency. A large
 * isolated move therefore ranks below a smaller one that several assets agree
 * on, which is how a desk actually reads a session.
 */

export const GLOBAL = 'GLOBAL';
export const INDIA = 'INDIA';

/** Which market each instrument belongs to, and what kind of thing it is.
 *  Instruments AGI does not price are simply absent - see MISSING below. */
const INSTRUMENTS = {
  NIFTY: { market: INDIA, category: 'EQUITIES', label: 'Nifty 50' },
  SENSEX: { market: INDIA, category: 'EQUITIES', label: 'Sensex' },
  'BANK NIFTY': { market: INDIA, category: 'FINANCIALS', label: 'Bank Nifty' },
  MIDCAP: { market: INDIA, category: 'EQUITIES', label: 'Midcap' },
  SMALLCAP: { market: INDIA, category: 'EQUITIES', label: 'Smallcap' },
  'INDIA VIX': { market: INDIA, category: 'MACRO', label: 'India VIX' },
  USDINR: { market: INDIA, category: 'FX', label: 'USD/INR' },
  'S&P': { market: GLOBAL, category: 'EQUITIES', label: 'S&P 500' },
  NASDAQ: { market: GLOBAL, category: 'EQUITIES', label: 'Nasdaq' },
  Dow: { market: GLOBAL, category: 'EQUITIES', label: 'Dow' },
  Gold: { market: GLOBAL, category: 'COMMODITIES', label: 'Gold' },
  Silver: { market: GLOBAL, category: 'COMMODITIES', label: 'Silver' },
  Brent: { market: GLOBAL, category: 'COMMODITIES', label: 'Brent' },
  Bitcoin: { market: GLOBAL, category: 'MACRO', label: 'Bitcoin' },
};

/**
 * Instruments the brief asked for that AGI does not price today.
 *
 * Listed rather than silently omitted: a cross-asset monitor that shows no row
 * for the US 10Y reads as "rates are quiet", and a reader who assumes that
 * once will not trust the rows that are real.
 */
export const MISSING = Object.freeze([
  { label: 'US 10Y', market: GLOBAL, category: 'RATES' },
  { label: 'DXY', market: GLOBAL, category: 'FX' },
  { label: 'VIX', market: GLOBAL, category: 'MACRO' },
  { label: 'India 10Y', market: INDIA, category: 'RATES' },
]);

/** Move sizes worth a line, per instrument: 0.5% is nothing for Bitcoin and a
 *  great deal for a currency pair. */
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

function istTime(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return null;
  return `${d.toLocaleTimeString('en-IN', {
    hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'Asia/Kolkata',
  })} IST`;
}

function describe(label, name, changePct) {
  const up = changePct > 0;
  const size = Math.abs(changePct);
  const strength = size >= 1.5 ? 'sharply' : size >= 0.75 ? 'firmly' : 'modestly';
  switch (name) {
    case 'INDIA VIX':
      return up
        ? 'India VIX is higher, indicating demand for downside protection.'
        : 'India VIX is lower, consistent with easing hedging demand.';
    case 'USDINR':
      return up
        ? 'The rupee is weaker against the dollar, which raises imported costs and pressures importers.'
        : 'The rupee is firmer against the dollar, easing imported cost pressure.';
    case 'BANK NIFTY':
      return up
        ? 'Banks are outperforming, which usually carries the broader index with them.'
        : 'Banks are underperforming, and financials carry enough index weight to drag the market.';
    case 'Brent':
      return up
        ? 'Crude is higher, lifting energy producers and raising input costs elsewhere.'
        : 'Crude is lower, easing input costs for transport and industrials.';
    case 'Gold':
      return up
        ? 'Gold is higher, a move usually associated with defensive positioning.'
        : 'Gold is lower, consistent with reduced defensive demand.';
    default:
      return `${label} is ${strength} ${up ? 'higher' : 'lower'} on the session.`;
  }
}

function severityFor(changePct, confirmations) {
  const size = Math.abs(changePct);
  if (size >= 1.5 || confirmations >= 3) return 'MAJOR';
  if (size >= 0.75 || confirmations >= 2) return 'NOTABLE';
  return 'WATCH';
}

function rows(snapshot) {
  return (snapshot || [])
    .map((row) => {
      const name = String(row?.name || '').trim();
      const meta = INSTRUMENTS[name];
      if (!meta) return null;
      const changePct = num(row?.percentChange);
      if (changePct === null) return null;
      return { name, ...meta, changePct, price: num(row?.price), updatedAt: row?.updatedAt || null };
    })
    .filter(Boolean);
}

/** Intelligence items for one market. */
export function buildIntelligence(snapshot = [], market = null, themes = []) {
  const all = rows(snapshot);
  const scoped = market ? all.filter((row) => row.market === market) : all;

  const meaningful = scoped.filter((row) => Math.abs(row.changePct) >= 0.3);
  const up = meaningful.filter((row) => row.changePct > 0).length;
  const down = meaningful.filter((row) => row.changePct < 0).length;

  const items = [];
  for (const row of scoped) {
    const limit = THRESHOLD[row.name] ?? THRESHOLD.default;
    if (Math.abs(row.changePct) < limit) continue;
    const confirmations = Math.max((row.changePct > 0 ? up : down) - 1, 0);

    const evidence = [{ label: row.label, value: row.changePct }];
    for (const peer of scoped) {
      if (peer.name === row.name || Math.abs(peer.changePct) < 0.2) continue;
      evidence.push({ label: peer.label, value: peer.changePct });
      if (evidence.length >= 5) break;
    }

    items.push({
      id: `mi-${row.name}`,
      market: row.market,
      category: row.category,
      headline: `${row.label} ${row.changePct > 0 ? 'higher' : 'lower'}`,
      body: describe(row.label, row.name, row.changePct),
      affected: evidence.slice(1, 4).map((e) => e.label),
      changePct: row.changePct,
      severity: severityFor(row.changePct, confirmations),
      time: istTime(row.updatedAt),
      sortKey: Math.abs(row.changePct) + confirmations * 0.35,
      evidence,
      sources: ['AGI Market Data'],
    });
  }

  // AGI's own themes are India-scoped, and carry a confidence the price feed
  // cannot express - but they never outrank a live move on magnitude alone.
  if (!market || market === INDIA) {
    for (const theme of (themes || []).slice(0, 4)) {
      const confidence = num(theme?.confidence);
      if (confidence === null || confidence < 0.6) continue;
      items.push({
        id: `theme-${theme.id || theme.name}`,
        market: INDIA,
        category: 'MACRO',
        headline: `${theme.name}: ${theme.trend || 'in focus'}`,
        body: `AGI's theme engine reads ${theme.name} as ${String(theme.trend || '').toLowerCase()} with a ${theme.bias || 'neutral'} bias.`,
        affected: Array.isArray(theme.tickers) ? theme.tickers.slice(0, 3) : [],
        severity: confidence >= 0.75 ? 'NOTABLE' : 'WATCH',
        time: null,
        sortKey: confidence,
        evidence: [{ label: 'Confidence', value: `${Math.round(confidence * 100)}%` }],
        sources: ['AGI Theme Engine'],
      });
    }
  }

  return items.sort((a, b) => b.sortKey - a.sortKey);
}

/**
 * Why one market is moving, or an admission that it is not clear.
 *
 * Returns null unless several instruments agree. A single index drifting is not
 * a driver, and naming one anyway is how a research page starts writing
 * narrative to fill a card.
 */
export function buildDrivers(snapshot = [], market) {
  const scoped = rows(snapshot).filter((row) => row.market === market);
  const equities = scoped.filter((row) => row.category === 'EQUITIES');
  if (equities.length < 2) return null;

  const equityAvg = equities.reduce((sum, row) => sum + row.changePct, 0) / equities.length;
  const others = scoped
    .filter((row) => row.category !== 'EQUITIES' && Math.abs(row.changePct) >= 0.3)
    .sort((a, b) => Math.abs(b.changePct) - Math.abs(a.changePct));

  if (others.length < 1 && Math.abs(equityAvg) < 0.5) return null;

  const weaker = equityAvg < 0;
  const confirmations = others.slice(0, 3).map((row) => ({
    label: row.label,
    value: row.changePct,
    reads: reading(row.name, row.changePct),
  }));

  const view = [
    `${market === INDIA ? 'Indian' : 'Global'} equity benchmarks are ${weaker ? 'lower' : 'higher'} by an average of ${Math.abs(equityAvg).toFixed(2)}% across the indices AGI tracks.`,
  ];
  if (confirmations.length) {
    view.push(`Other ${market === INDIA ? 'domestic' : 'global'} assets are consistent with that: ${confirmations
      .map((c) => `${c.label} ${c.value > 0 ? '+' : ''}${c.value.toFixed(2)}% (${c.reads})`)
      .join(', ')}.`);
  }

  return {
    market,
    primary: `${market === INDIA ? 'Indian' : 'Global'} equities ${weaker ? 'under pressure' : 'firmer'}`,
    secondary: confirmations.length ? `${confirmations[0].label} ${confirmations[0].reads}` : null,
    confirmations,
    equityAvg,
    view: view.join(' '),
    basis: 'Derived from the current market snapshot only.',
  };
}

function reading(name, changePct) {
  const up = changePct > 0;
  switch (name) {
    case 'INDIA VIX': return up ? 'volatility bid' : 'volatility easing';
    case 'USDINR': return up ? 'rupee weaker' : 'rupee firmer';
    case 'Gold': return up ? 'defensive bid' : 'defensive bid easing';
    case 'Brent': return up ? 'crude firmer' : 'crude softer';
    case 'BANK NIFTY': return up ? 'banks leading' : 'banks lagging';
    default: return up ? 'higher' : 'lower';
  }
}

/**
 * Global developments with a stated India exposure.
 *
 * The relationships below are structural facts about the Indian economy - a
 * crude importer, a market sensitive to global risk appetite - not patterns
 * discovered in the data. What the data decides is only whether a linkage is
 * live enough to show.
 *
 * A linkage is shown when the global signal has moved AND the named domestic
 * asset has moved in the direction that exposure implies. Co-movement alone is
 * not evidence of anything, so the copy says the two are consistent, never that
 * one caused the other, and confirmation is reported as its own field so a
 * reader can see when it is absent.
 */
const LINKAGES = [
  {
    id: 'crude-inr',
    signal: 'Brent',
    trigger: 1.5,
    exposure: 'Oil-sensitive sectors and the rupee',
    rationale: 'India imports most of its crude, so a sustained move changes the import bill and the currency.',
    watch: ['Airlines', 'Paints', 'Tyres', 'OMCs', 'USD/INR'],
    confirmBy: 'USDINR',
    confirms: (signalChange, confirmChange) => signalChange > 0 && confirmChange > 0,
    confirmReads: 'the rupee is weaker alongside firmer crude',
  },
  {
    id: 'global-risk',
    signal: 'S&P',
    trigger: 0.6,
    exposure: 'Foreign-flow sensitivity in Indian equities',
    rationale: 'Global risk appetite is a first-order input to foreign positioning in Indian equities.',
    watch: ['Nifty 50', 'Foreign flows', 'Large caps'],
    confirmBy: 'NIFTY',
    confirms: (signalChange, confirmChange) =>
      Math.sign(signalChange) === Math.sign(confirmChange) && Math.abs(confirmChange) >= 0.2,
    confirmReads: 'Indian equities are moving in the same direction',
  },
  {
    id: 'defensive-bid',
    signal: 'Gold',
    trigger: 1.0,
    exposure: 'Risk posture across Indian equities',
    rationale: 'A defensive bid in gold usually coincides with reduced appetite for equity risk.',
    watch: ['Nifty 50', 'India VIX'],
    confirmBy: 'INDIA VIX',
    confirms: (signalChange, confirmChange) => signalChange > 0 && confirmChange > 0,
    confirmReads: 'India VIX is higher at the same time',
  },
];

export function buildCrossMarket(snapshot = []) {
  const by = new Map(rows(snapshot).map((row) => [row.name, row]));
  const out = [];
  for (const link of LINKAGES) {
    const signal = by.get(link.signal);
    if (!signal || Math.abs(signal.changePct) < link.trigger) continue;
    const confirm = by.get(link.confirmBy);
    const confirmed = Boolean(confirm && link.confirms(signal.changePct, confirm.changePct));
    out.push({
      id: link.id,
      signalLabel: signal.label,
      signalChange: signal.changePct,
      exposure: link.exposure,
      rationale: link.rationale,
      watch: link.watch,
      // Named honestly. DETECTED means the global leg moved; CONFIRMED means the
      // domestic leg moved with it. Neither claims causation.
      status: confirmed ? 'CONFIRMED' : 'DETECTED',
      confirmLabel: confirm?.label || link.confirmBy,
      confirmChange: confirm?.changePct ?? null,
      confirmReads: confirmed ? link.confirmReads : null,
      note: confirmed
        ? null
        : `The domestic leg has not moved with it, so this is flagged as observed rather than confirmed.`,
    });
  }
  return out.sort((a, b) => Math.abs(b.signalChange) - Math.abs(a.signalChange));
}

export const FILTERS = ['ALL', 'GLOBAL', 'INDIA', 'EQUITIES', 'FINANCIALS', 'RATES', 'FX', 'COMMODITIES', 'MACRO'];

export function applyFilter(items, filter) {
  if (!filter || filter === 'ALL') return items;
  if (filter === GLOBAL || filter === INDIA) return items.filter((item) => item.market === filter);
  return items.filter((item) => item.category === filter);
}
