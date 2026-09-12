/**
 * Pre-market global context — redistribution-friendly global APIs only.
 * Never surfaces NSE/BSE raw real-time quotes.
 * Frontend never calls third-party APIs; all reads go through AGI cache.
 */

import {
  getOrFetchDataset,
  getCachedDataset,
  isFresh,
  MACRO_REFRESH_MS,
} from './macroRepository.js';
import { getMarketContext } from './marketContextService.js';

async function fetchJson(url, { timeoutMs = 12_000 } = {}) {
  const response = await fetch(url, {
    headers: { Accept: 'application/json' },
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) throw new Error(`${url} failed (${response.status})`);
  return response.json();
}

function pctChange(current, previous) {
  const c = Number(current);
  const p = Number(previous);
  if (!Number.isFinite(c) || !Number.isFinite(p) || p === 0) return null;
  return ((c - p) / p) * 100;
}

function toneFromPct(pct) {
  const n = Number(pct);
  if (!Number.isFinite(n)) return 'Neutral';
  if (n >= 0.25) return 'Bullish';
  if (n <= -0.25) return 'Bearish';
  return 'Neutral';
}

function formatPct(pct) {
  const n = Number(pct);
  if (!Number.isFinite(n)) return null;
  const sign = n > 0 ? '+' : '';
  return `${sign}${n.toFixed(2)}%`;
}

function sparkFromPct(pct) {
  const n = Number(pct) || 0;
  if (n > 0) return [1, 1.05, 1.02, 1.08, 1.1, 1.12, 1.15, 1.18];
  if (n < 0) return [1.18, 1.15, 1.12, 1.1, 1.08, 1.05, 1.02, 1];
  return [1, 1.01, 0.99, 1, 1.005, 0.995, 1, 1];
}

async function quoteFinnhub(symbol, apiKey) {
  const data = await fetchJson(`https://finnhub.io/api/v1/quote?symbol=${encodeURIComponent(symbol)}&token=${apiKey}`);
  const current = Number(data.c);
  const previous = Number(data.pc);
  if (!Number.isFinite(current) || current <= 0) throw new Error(`Finnhub empty quote for ${symbol}`);
  const changePct = Number.isFinite(Number(data.dp)) ? Number(data.dp) : pctChange(current, previous);
  return {
    price: current,
    previousClose: previous,
    changePct,
    asOf: data.t ? new Date(data.t * 1000).toISOString() : new Date().toISOString(),
    source: 'Finnhub',
  };
}

async function quoteTwelveData(symbol, apiKey) {
  const data = await fetchJson(
    `https://api.twelvedata.com/quote?symbol=${encodeURIComponent(symbol)}&apikey=${apiKey}`,
  );
  if (data?.status === 'error' || data?.code) throw new Error(data?.message || `Twelve Data failed for ${symbol}`);
  const current = Number(data.close ?? data.price);
  const previous = Number(data.previous_close);
  const changePct = Number.isFinite(Number(data.percent_change))
    ? Number(data.percent_change)
    : pctChange(current, previous);
  if (!Number.isFinite(current)) throw new Error(`Twelve Data empty quote for ${symbol}`);
  return {
    price: current,
    previousClose: previous,
    changePct,
    asOf: data.datetime || new Date().toISOString(),
    source: 'Twelve Data',
  };
}

async function quoteYahoo(symbol) {
  const { fetchYahooSymbol } = await import('../providers/yahooIndices.js');
  const quote = await fetchYahooSymbol(symbol);
  if (!quote?.price) throw new Error(`Yahoo empty quote for ${symbol}`);
  return {
    price: quote.price,
    previousClose: quote.previousClose,
    changePct: quote.changePct,
    asOf: quote.asOf,
    source: 'Yahoo',
  };
}

async function resolveQuote(instrument) {
  const finnhubKey = (process.env.FINNHUB_API_KEY || '').trim();
  const twelveKey = (process.env.TWELVE_DATA_API_KEY || '').trim();
  const errors = [];

  // Prefer Yahoo cash/futures symbols when configured — avoids showing SPY/QQQ/DIA as index levels.
  if (instrument.yahoo) {
    try {
      return { ...instrument, ...(await quoteYahoo(instrument.yahoo)) };
    } catch (error) {
      errors.push(error.message);
    }
  }

  if (finnhubKey && instrument.finnhub) {
    try {
      return { ...instrument, ...(await quoteFinnhub(instrument.finnhub, finnhubKey)) };
    } catch (error) {
      errors.push(error.message);
    }
  }
  if (twelveKey && instrument.twelve) {
    try {
      return { ...instrument, ...(await quoteTwelveData(instrument.twelve, twelveKey)) };
    } catch (error) {
      errors.push(error.message);
    }
  }
  throw new Error(errors.join(' | ') || `No quote provider for ${instrument.id}`);
}

const GLOBAL_INSTRUMENTS = [
  {
    id: 'spx',
    label: 'S&P 500',
    group: 'US cash',
    yahoo: '^GSPC',
    finnhub: 'SPY',
    twelve: 'SPY',
    note: 'US large-cap risk appetite overnight.',
  },
  {
    id: 'ndx',
    label: 'NASDAQ',
    group: 'US cash',
    yahoo: '^IXIC',
    finnhub: 'QQQ',
    twelve: 'QQQ',
    note: 'Growth and AI-sensitive overnight tone.',
  },
  {
    id: 'dji',
    label: 'Dow',
    group: 'US cash',
    yahoo: '^DJI',
    finnhub: 'DIA',
    twelve: 'DIA',
    note: 'Cyclical / industrial overnight tone.',
  },
  {
    id: 'ftse',
    label: 'FTSE',
    group: 'Europe',
    yahoo: '^FTSE',
    finnhub: 'EWU',
    twelve: 'EWU',
    note: 'UK risk appetite proxy.',
  },
  {
    id: 'dax',
    label: 'DAX',
    group: 'Europe',
    yahoo: '^GDAXI',
    finnhub: 'EWG',
    twelve: 'EWG',
    note: 'Euro-area industrial / ECB-sensitive tone.',
  },
  {
    id: 'nikkei',
    label: 'Nikkei',
    group: 'Asia',
    yahoo: '^N225',
    finnhub: 'EWJ',
    twelve: 'EWJ',
    note: 'Japan exporters and yen-sensitive risk.',
  },
  {
    id: 'hangseng',
    label: 'Hang Seng',
    group: 'Asia',
    yahoo: '^HSI',
    finnhub: 'EWH',
    twelve: 'EWH',
    note: 'China / HK risk and property sensitivity.',
  },
];

const DRIVER_INSTRUMENTS = [
  { id: 'oil', label: 'Oil', yahoo: 'CL=F', finnhub: 'USO', twelve: 'USO', indiaImpactDefault: 'Airlines · Paint · Auto' },
  { id: 'dollar', label: 'Dollar (DXY proxy)', yahoo: 'DX-Y.NYB', finnhub: 'UUP', twelve: 'UUP', indiaImpactDefault: 'IT · Metals · Importers' },
  { id: 'treasury', label: 'US Treasury', yahoo: '^TNX', finnhub: 'TLT', twelve: 'TLT', indiaImpactDefault: 'Banks · NBFCs · Duration' },
  { id: 'gold', label: 'Gold', yahoo: 'GC=F', finnhub: 'GLD', twelve: 'GLD', indiaImpactDefault: 'Jewellery · Mining' },
  { id: 'copper', label: 'Copper', yahoo: 'HG=F', finnhub: 'CPER', twelve: 'CPER', indiaImpactDefault: 'Metals · Capital Goods' },
  { id: 'bitcoin', label: 'Bitcoin', yahoo: 'BTC-USD', finnhub: 'BINANCE:BTCUSDT', twelve: 'BTC/USD', indiaImpactDefault: 'Risk appetite · Fintech' },
];

function mapInstrument(raw) {
  const changePct = raw.changePct;
  const tone = toneFromPct(changePct);
  return {
    id: raw.id,
    label: raw.label,
    group: raw.group || null,
    price: Number.isFinite(raw.price) ? Number(raw.price.toFixed(2)) : null,
    changePct: Number.isFinite(changePct) ? Number(changePct.toFixed(2)) : null,
    changeLabel: formatPct(changePct) || '—',
    tone,
    note: raw.note || null,
    sparkline: sparkFromPct(changePct),
    source: raw.source,
    asOf: raw.asOf,
    symbolUsed: raw.yahoo || raw.finnhub || raw.twelve,
    redistributionNote:
      'Global cash/futures quote via Yahoo (preferred) or licensed API fallback. Not an exchange-owned NSE/BSE quote.',
  };
}

async function loadGlobalIndices() {
  // v2 = cash/futures Yahoo symbols (not SPY/QQQ/DIA ETF proxies)
  return getOrFetchDataset(
    'global_indices_v2',
    async () => {
      const results = [];
      for (const instrument of GLOBAL_INSTRUMENTS) {
        try {
          // Sequential to respect free-tier rate limits
          results.push(mapInstrument(await resolveQuote(instrument)));
          await new Promise((r) => setTimeout(r, 250));
        } catch (error) {
          console.warn(`[pre-market] index ${instrument.id}:`, error.message);
          results.push({
            id: instrument.id,
            label: instrument.label,
            group: instrument.group,
            price: null,
            changePct: null,
            changeLabel: 'Unavailable',
            tone: 'Neutral',
            note: instrument.note,
            sparkline: sparkFromPct(0),
            source: 'unavailable',
            asOf: null,
            unavailable: true,
          });
        }
      }
      if (!results.some((item) => !item.unavailable)) throw new Error('All global index quotes unavailable');
      return { instruments: results };
    },
    {
      source: 'Yahoo/Finnhub/Twelve Data',
      ttlMs: MACRO_REFRESH_MS.global_indices,
      refreshPolicy: '20m pre-market',
    },
  );
}

async function loadGlobalDrivers() {
  // v2 = futures/cash Yahoo symbols (not USO/GLD/UUP ETF proxies as primary)
  return getOrFetchDataset(
    'global_drivers_v2',
    async () => {
      const drivers = [];
      for (const instrument of DRIVER_INSTRUMENTS) {
        try {
          const quote = await resolveQuote(instrument);
          const mapped = mapInstrument({ ...instrument, ...quote });
          const positiveForIndia = mapped.changePct != null
            && ((instrument.id === 'oil' && mapped.changePct < 0)
              || (instrument.id === 'dollar' && mapped.changePct < 0)
              || (instrument.id === 'treasury' && mapped.changePct > 0)
              || (instrument.id === 'copper' && mapped.changePct > 0)
              || (instrument.id === 'bitcoin' && mapped.changePct > 0)
              || (instrument.id === 'gold' && mapped.changePct > 0.5));
          drivers.push({
            ...mapped,
            indiaImpact: instrument.indiaImpactDefault,
            indiaTone: instrument.id === 'gold'
              ? (mapped.changePct > 0.5 ? 'Risk-off' : 'Neutral')
              : positiveForIndia
                ? 'Positive'
                : mapped.changePct < -0.25
                  ? 'Negative'
                  : 'Neutral',
            transmission: instrument.id === 'oil'
              ? ['Oil move', 'Input costs / fuel', 'Inflation & margins', instrument.indiaImpactDefault]
              : instrument.id === 'dollar'
                ? ['Dollar move', 'Imported costs / IT revenues', 'EM financial conditions', instrument.indiaImpactDefault]
                : instrument.id === 'treasury'
                  ? ['US yields / duration', 'Global financial conditions', 'India rate-sensitive flows', instrument.indiaImpactDefault]
                  : [instrument.label, 'Global risk channel', 'India sector transmission', instrument.indiaImpactDefault],
          });
          await new Promise((r) => setTimeout(r, 250));
        } catch (error) {
          console.warn(`[pre-market] driver ${instrument.id}:`, error.message);
        }
      }

      // USDINR from Frankfurter (already cached via macro when available)
      try {
        const fx = await fetchJson('https://api.frankfurter.app/latest?from=USD&to=INR');
        const rate = Number(fx?.rates?.INR);
        if (Number.isFinite(rate)) {
          drivers.push({
            id: 'usdinr',
            label: 'USD/INR',
            price: Number(rate.toFixed(2)),
            changePct: null,
            changeLabel: 'Spot',
            tone: 'Neutral',
            indiaImpact: 'Imported inflation · Exporters',
            indiaTone: 'Watch',
            transmission: ['USD/INR', 'Imported inflation', 'RBI policy room', 'IT / Importers'],
            sparkline: sparkFromPct(0),
            source: 'Frankfurter/ECB',
            asOf: fx.date || new Date().toISOString(),
          });
        }
      } catch (error) {
        console.warn('[pre-market] USDINR:', error.message);
      }

      if (!drivers.length) throw new Error('No global drivers available');
      return { drivers };
    },
    {
      source: 'Finnhub/Twelve Data/Frankfurter',
      ttlMs: MACRO_REFRESH_MS.global_drivers,
      refreshPolicy: '30m',
    },
  );
}

async function loadFinnhubCalendar() {
  const apiKey = (process.env.FINNHUB_API_KEY || '').trim();
  if (!apiKey) {
    const cached = await getCachedDataset('finnhub_calendar');
    if (cached?.payload) return { ...cached, fromCache: true, refreshed: false, stale: !isFresh(cached) };
    return {
      datasetKey: 'finnhub_calendar',
      payload: { economic: [], earnings: [] },
      source: 'unavailable',
      fetchedAt: null,
      stale: true,
      fromCache: false,
    };
  }

  return getOrFetchDataset(
    'finnhub_calendar',
    async () => {
      const today = new Date();
      const to = new Date(today);
      to.setDate(to.getDate() + 7);
      const fromStr = today.toISOString().slice(0, 10);
      const toStr = to.toISOString().slice(0, 10);

      const [economic, earnings] = await Promise.all([
        fetchJson(`https://finnhub.io/api/v1/calendar/economic?from=${fromStr}&to=${toStr}&token=${apiKey}`).catch(() => ({ economicCalendar: [] })),
        fetchJson(`https://finnhub.io/api/v1/calendar/earnings?from=${fromStr}&to=${toStr}&token=${apiKey}`).catch(() => ({ earningsCalendar: [] })),
      ]);

      const ecoRows = (economic.economicCalendar || [])
        .filter((row) => /united states|india|euro|china|japan|uk|united kingdom/i.test(`${row.country || ''}`))
        .slice(0, 12)
        .map((row) => ({
          date: row.time || row.date,
          country: row.country,
          event: row.event,
          impact: Number(row.impact) >= 3 ? 'High' : Number(row.impact) === 2 ? 'Medium' : 'Low',
          estimate: row.estimate ?? null,
          prev: row.prev ?? null,
        }));

      const earnRows = (earnings.earningsCalendar || [])
        .slice(0, 10)
        .map((row) => ({
          date: row.date,
          symbol: row.symbol,
          hour: row.hour || null,
          epsEstimate: row.epsEstimate ?? null,
          revenueEstimate: row.revenueEstimate ?? null,
        }));

      return { economic: ecoRows, earnings: earnRows };
    },
    {
      source: 'Finnhub',
      ttlMs: MACRO_REFRESH_MS.finnhub_calendar,
      refreshPolicy: '6h',
    },
  );
}

function buildHeatMap(indicesPayload, driversPayload) {
  const byId = Object.fromEntries((indicesPayload?.instruments || []).map((item) => [item.id, item]));
  const drivers = Object.fromEntries((driversPayload?.drivers || []).map((item) => [item.id, item]));
  const usTone = [byId.spx, byId.ndx, byId.dji]
    .filter(Boolean)
    .reduce((sum, item) => sum + (Number(item.changePct) || 0), 0);

  return [
    { driver: 'US Futures / overnight risk', indiaImpact: usTone >= 0.3 ? 'Positive' : usTone <= -0.3 ? 'Negative' : 'Neutral' },
    { driver: 'Oil', indiaImpact: drivers.oil?.indiaTone || 'Watch' },
    { driver: 'Dollar', indiaImpact: drivers.dollar?.indiaTone || 'Neutral' },
    { driver: 'US Treasury', indiaImpact: drivers.treasury?.indiaTone || 'Watch' },
    { driver: 'China / Hang Seng', indiaImpact: byId.hangseng?.tone === 'Bullish' ? 'Positive' : byId.hangseng?.tone === 'Bearish' ? 'Negative' : 'Watch' },
    { driver: 'Middle East / geopolitics', indiaImpact: 'Watch' },
    { driver: 'Monsoon / food prices', indiaImpact: 'Watch' },
  ];
}

export async function getPreMarketContext({ force = false } = {}) {
  const [indicesRec, driversRec, calendarRec, marketContext] = await Promise.all([
    loadGlobalIndices(),
    loadGlobalDrivers(),
    loadFinnhubCalendar(),
    getMarketContext().catch(() => ({ headlines: [], commodities: [] })),
  ]);

  const datasetStatus = [indicesRec, driversRec, calendarRec].map((rec) => ({
    key: rec.datasetKey,
    source: rec.source,
    fetchedAt: rec.fetchedAt,
    stale: Boolean(rec.stale),
    fromCache: Boolean(rec.fromCache),
    refreshed: Boolean(rec.refreshed),
  }));

  return {
    updatedAt: new Date().toISOString(),
    force,
    globalMarkets: indicesRec.payload?.instruments || [],
    drivers: driversRec.payload?.drivers || [],
    heatMap: buildHeatMap(indicesRec.payload, driversRec.payload),
    economicCalendar: calendarRec.payload?.economic || [],
    earningsCalendar: calendarRec.payload?.earnings || [],
    headlines: (marketContext.headlines || []).slice(0, 8),
    commodities: marketContext.commodities || [],
    sourcesUsed: [...new Set(datasetStatus.map((item) => item.source).filter((s) => s && s !== 'unavailable'))],
    datasetStatus,
    stale: datasetStatus.some((item) => item.stale && item.fromCache && item.fetchedAt),
    compliance: {
      indianQuotes: 'AGI does not display raw NSE/BSE real-time quotes on this page.',
      globalQuotes: 'Global levels prefer Yahoo cash/futures prints; licensed ETF APIs remain fallback only.',
    },
  };
}
