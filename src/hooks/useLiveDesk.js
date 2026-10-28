import { useCallback, useEffect, useRef, useState } from 'react';
import { getUiHome } from '@/lib/uiApi';
import { API_ORIGIN } from '@/config';
import { REFRESH_MS } from '@/lib/liveDeskConfig';

/**
 * Live Desk data, assembled from services AGI already runs.
 *
 * No new ingestion and no new backend endpoint: /api/ui/home already carries
 * the market snapshot, the economic calendar and featured research, the market
 * intelligence engine already computes regime and drivers, and Live Alpha
 * already has a workspace endpoint. Adding a /api/live-desk aggregator would
 * have meant a second copy of all of it drifting from the first.
 *
 * Every section reports its own state. A panel whose source is unavailable
 * says so rather than borrowing another panel's data or showing a plausible
 * number, because a desk that cannot tell live from stale is worse than one
 * showing less.
 */

const ok = (value) => value !== null && value !== undefined && value !== '';

async function getJson(path, { timeoutMs = 20_000 } = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_ORIGIN || ''}${path}`, {
      headers: { Accept: 'application/json' },
      credentials: 'include',
      signal: controller.signal,
    });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

/** Cross-asset rows the snapshot actually carries.
 *
 *  US 10Y and DXY are deliberately absent: the feed does not provide them, and
 *  a monitor that shows a row for an instrument it cannot price is the kind of
 *  thing a reader trusts once and never again. INDIA VIX is labelled as such
 *  rather than as "VIX", which is a different index. */
const CROSS_ASSET = [
  { key: 'NIFTY', label: 'Nifty 50', klass: 'India equities' },
  { key: 'BANK NIFTY', label: 'Bank Nifty', klass: 'India financials' },
  { key: 'USDINR', label: 'USD/INR', klass: 'India FX' },
  { key: 'INDIA VIX', label: 'India VIX', klass: 'India volatility' },
  { key: 'S&P', label: 'S&P 500', klass: 'Global equities' },
  { key: 'NASDAQ', label: 'Nasdaq', klass: 'Global equities' },
  { key: 'Brent', label: 'Brent', klass: 'Global commodities' },
  { key: 'Gold', label: 'Gold', klass: 'Global commodities' },
];

function num(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

/** A one-word read of a move. Descriptive, never a recommendation. */
function signalFor(label, changePct) {
  if (changePct === null) return null;
  const rising = changePct > 0;
  const flat = Math.abs(changePct) < 0.1;
  if (flat) return 'Little changed';
  switch (label) {
    case 'India VIX': return rising ? 'Volatility up' : 'Volatility down';
    case 'USD/INR': return rising ? 'Rupee weaker' : 'Rupee firmer';
    case 'Gold': return rising ? 'Defensive bid' : 'Defensive bid easing';
    case 'Brent': return rising ? 'Crude firmer' : 'Crude softer';
    default: return rising ? 'Risk-on' : 'Risk-off';
  }
}

function buildCrossAsset(snapshot) {
  const bySymbol = new Map((snapshot || []).map((row) => [String(row?.name || '').trim(), row]));
  return CROSS_ASSET.map(({ key, label, klass }) => {
    const row = bySymbol.get(key);
    if (!row) return { label, klass, available: false };
    const changePct = num(row.percentChange);
    return {
      label,
      klass,
      available: ok(row.price),
      last: num(row.price),
      changePct,
      signal: signalFor(label, changePct),
      stale: Boolean(row.stale || row.liveUnavailable),
      session: row.session || null,
    };
  });
}

/** Moves large enough to be worth a reader's attention.
 *
 *  Thresholds are stated here rather than described as percentiles: the
 *  snapshot carries no historical distribution, so a percentile claim would be
 *  a number with nothing behind it. */
const ALERT_RULES = [
  { key: 'INDIA VIX', label: 'India VIX', abs: 5, severity: 'NOTABLE',
    note: 'Volatility moving sharply.' },
  { key: 'NIFTY', label: 'Nifty 50', abs: 1.0, severity: 'MAJOR', note: 'Index move beyond a normal session range.' },
  { key: 'SENSEX', label: 'Sensex', abs: 1.0, severity: 'MAJOR', note: 'Index move beyond a normal session range.' },
  { key: 'Brent', label: 'Brent', abs: 2.5, severity: 'NOTABLE', note: 'Crude moving on the session.' },
  { key: 'Gold', label: 'Gold', abs: 1.5, severity: 'NOTABLE', note: 'Defensive assets repricing.' },
  { key: 'USDINR', label: 'USD/INR', abs: 0.5, severity: 'NOTABLE', note: 'Currency move is large for a single session.' },
];

function buildAlerts(snapshot) {
  const bySymbol = new Map((snapshot || []).map((row) => [String(row?.name || '').trim(), row]));
  const out = [];
  for (const rule of ALERT_RULES) {
    const row = bySymbol.get(rule.key);
    const changePct = num(row?.percentChange);
    if (changePct === null || Math.abs(changePct) < rule.abs) continue;
    out.push({
      severity: rule.severity,
      label: rule.label,
      changePct,
      note: rule.note,
      threshold: rule.abs,
    });
  }
  return out.sort((a, b) => Math.abs(b.changePct) - Math.abs(a.changePct));
}


const EMPTY = {
  snapshot: [], events: [], research: [], themes: [],
  crossAsset: [], alerts: [], regime: null, flows: null, liveAlpha: null,
};

export default function useLiveDesk() {
  const [state, setState] = useState({
    ...EMPTY,
    loading: true,
    updatedAt: null,
    stale: false,
    errors: {},
  });
  const mounted = useRef(true);

  const load = useCallback(async () => {
    const errors = {};
    const [homeResult, alphaResult, miResult] = await Promise.allSettled([
      getUiHome(),
      getJson('/api/market/live-alpha/workspace', { timeoutMs: 25_000 }),
      getJson('/api/intelligence/market-intelligence/dashboard', { timeoutMs: 25_000 }),
    ]);

    const home = homeResult.status === 'fulfilled' ? homeResult.value || {} : {};
    if (homeResult.status === 'rejected') errors.home = String(homeResult.reason?.message || homeResult.reason);

    const snapshotRaw = Array.isArray(home.market_snapshot) ? home.market_snapshot : [];
    // Same filter the header strip uses: a row without a price is not a quote.
    const snapshot = snapshotRaw.filter((row) => Number(row?.price) > 0);
    const stale = snapshot.some((row) => row?.stale || row?.liveUnavailable);

    let liveAlpha = null;
    if (alphaResult.status === 'fulfilled') {
      const w = alphaResult.value || {};
      const signals = Array.isArray(w.signals) ? w.signals : [];
      const byEngine = new Map();
      for (const run of Array.isArray(w.runs) ? w.runs : []) {
        byEngine.set(run.engine, (byEngine.get(run.engine) || 0) + 0);
      }
      for (const signal of signals) {
        const run = (Array.isArray(w.runs) ? w.runs : []).find((r) => r.id === signal.run_id);
        const engine = run?.engine || signal.engine;
        if (engine) byEngine.set(engine, (byEngine.get(engine) || 0) + 1);
      }
      liveAlpha = {
        engines: Array.from(byEngine, ([engine, count]) => ({ engine, count })),
        total: signals.length,
        stale: Boolean(w.freshness?.stale),
        generatedAt: w.generated_at || null,
      };
    } else {
      errors.liveAlpha = String(alphaResult.reason?.message || alphaResult.reason);
    }

    let regime = null;
    let flows = null;
    if (miResult.status === 'fulfilled') {
      const mi = miResult.value || {};
      const mr = mi.market_regime || {};
      // "Unavailable" is the engine's own word for a degraded response; it is
      // not a regime and must not be shown as one.
      if (mi.ok && ok(mr.regime) && String(mr.regime).toLowerCase() !== 'unavailable') {
        regime = {
          regime: mr.regime,
          participation: mr.participation || null,
          drivers: Array.isArray(mi.market_drivers?.drivers) ? mi.market_drivers.drivers : [],
          breadth: mi.breadth || null,
          health: mi.market_health || null,
        };
      }
      // FII/DII, which is India-only and has its own availability flags. The
      // engine reports latest_values_available separately from available,
      // because a day can be present with no figures on it.
      const f = mi.flows || {};
      if (f.available) {
        flows = {
          latestDate: f.latest_date || null,
          hasLatest: Boolean(f.latest_values_available),
          fiiNet: ok(f.fii_net) ? Number(f.fii_net) : null,
          diiNet: ok(f.dii_net) ? Number(f.dii_net) : null,
          trend5d: ok(f.trend_5d) ? Number(f.trend_5d) : null,
          trend20d: ok(f.trend_20d) ? Number(f.trend_20d) : null,
        };
      }
    } else {
      errors.regime = String(miResult.reason?.message || miResult.reason);
    }

    if (!mounted.current) return;
    setState({
      loading: false,
      snapshot,
      crossAsset: buildCrossAsset(snapshot),
      alerts: buildAlerts(snapshot),
      events: Array.isArray(home.economic_calendar) ? home.economic_calendar : [],
      research: Array.isArray(home.featured_research) ? home.featured_research : [],
      themes: Array.isArray(home.market_themes) ? home.market_themes : [],
      regime,
      flows,
      liveAlpha,
      updatedAt: snapshot[0]?.updatedAt || null,
      stale,
      errors,
    });
  }, []);

  useEffect(() => {
    mounted.current = true;
    load();
    const timer = setInterval(load, REFRESH_MS.pulse);
    return () => {
      mounted.current = false;
      clearInterval(timer);
    };
  }, [load]);

  return { ...state, refresh: load };
}
