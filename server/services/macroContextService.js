/**
 * Macro context aggregator — AI-first, API-second.
 * Every upstream call goes through macroRepository with dataset-specific TTLs.
 */

import { getMarketContext } from './marketContextService.js';
import {
  getOrFetchDataset,
  getCachedDataset,
  isFresh,
  MACRO_REFRESH_MS,
} from './macroRepository.js';

const ASSEMBLED_CACHE_MS = 30 * 60 * 1000; // assemble from cached datasets at most every 30m
let assembled = null;
let assembledExpiresAt = 0;
let inflight = null;

async function fetchJson(url, { headers = {}, timeoutMs = 12_000 } = {}) {
  const response = await fetch(url, {
    headers: { Accept: 'application/json', ...headers },
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) throw new Error(`${url} failed (${response.status})`);
  return response.json();
}

function directionFromDelta(delta, thresholds = { up: 0.15, down: -0.15 }) {
  const n = Number(delta);
  if (!Number.isFinite(n)) return 'Stable';
  if (n >= thresholds.up) return 'Firming';
  if (n <= thresholds.down) return 'Easing';
  return 'Stable';
}

function toSentiment(label) {
  const text = String(label || '').toLowerCase();
  if (/firm|up|strong|improv|hawk|elevat|hot/i.test(text)) return 'Firming';
  if (/eas|down|weak|soft|cool|dovish/i.test(text)) return 'Easing';
  return 'Stable';
}

async function loadUsdInr() {
  return getOrFetchDataset(
    'fx_usdinr',
    async () => {
      const data = await fetchJson('https://api.frankfurter.app/latest?from=USD&to=INR');
      const rate = Number(data?.rates?.INR);
      if (!Number.isFinite(rate)) throw new Error('USDINR missing');
      return {
        pair: 'USD/INR',
        value: rate,
        direction: 'Stable',
        implication: 'A firmer dollar typically raises imported inflation pressure for India, while a softer dollar can ease commodity-linked cost pressure.',
        asOf: data.date || new Date().toISOString().slice(0, 10),
      };
    },
    {
      source: 'Frankfurter/ECB',
      ttlMs: MACRO_REFRESH_MS.fx_usdinr,
      toObservations: (payload) => [{ label: 'USD/INR', valueNumeric: payload.value, direction: payload.direction }],
    },
  );
}

async function loadWorldBankIndia() {
  return getOrFetchDataset(
    'world_bank_india',
    async () => {
      const indicators = [
        { id: 'FP.CPI.TOTL.ZG', label: 'India CPI inflation (annual %)' },
        { id: 'NY.GDP.MKTP.KD.ZG', label: 'India real GDP growth (annual %)' },
      ];
      const results = [];
      for (const indicator of indicators) {
        const payload = await fetchJson(
          `https://api.worldbank.org/v2/country/IND/indicator/${indicator.id}?format=json&per_page=6`,
        );
        const rows = Array.isArray(payload?.[1]) ? payload[1].filter((row) => row.value != null) : [];
        const latest = rows[0];
        const previous = rows[1];
        if (!latest) continue;
        const delta = previous ? Number(latest.value) - Number(previous.value) : 0;
        results.push({
          label: indicator.label,
          year: latest.date,
          value: Number(latest.value),
          direction: directionFromDelta(delta, { up: 0.3, down: -0.3 }),
          source: 'World Bank',
        });
      }
      if (!results.length) throw new Error('World Bank returned no India rows');
      return results;
    },
    {
      source: 'World Bank',
      ttlMs: MACRO_REFRESH_MS.world_bank_india,
      refreshPolicy: 'monthly',
      toObservations: (payload) => payload.map((item) => ({
        label: item.label,
        valueNumeric: item.value,
        direction: item.direction,
        valueText: String(item.year),
      })),
    },
  );
}

async function loadFredRates() {
  const apiKey = (process.env.FRED_API_KEY || '').trim();
  if (!apiKey) {
    const cached = await getCachedDataset('fred_rates');
    if (cached?.payload) {
      return { ...cached, fromCache: true, refreshed: false, stale: !isFresh(cached) };
    }
    return {
      datasetKey: 'fred_rates',
      payload: [],
      source: 'unavailable',
      fetchedAt: null,
      expiresAt: null,
      stale: true,
      fromCache: false,
      refreshed: false,
      meta: { reason: 'FRED_API_KEY not configured' },
    };
  }

  return getOrFetchDataset(
    'fred_rates',
    async () => {
      const series = [
        { id: 'FEDFUNDS', label: 'US Federal Funds Rate' },
        { id: 'DGS10', label: 'US 10Y Treasury Yield' },
        { id: 'CPIAUCSL', label: 'US CPI' },
      ];
      const out = [];
      for (const item of series) {
        const data = await fetchJson(
          `https://api.stlouisfed.org/fred/series/observations?series_id=${item.id}&api_key=${apiKey}&file_type=json&sort_order=desc&limit=8`,
        );
        const observations = (data.observations || []).filter((row) => row.value !== '.');
        if (observations.length < 2) continue;
        const latest = Number(observations[0].value);
        const previous = Number(observations[1].value);
        const history = observations
          .slice(0, 8)
          .reverse()
          .map((row) => Number(row.value))
          .filter(Number.isFinite);
        out.push({
          label: item.label,
          date: observations[0].date,
          value: latest,
          direction: directionFromDelta(latest - previous),
          source: 'FRED',
          history,
        });
      }
      if (!out.length) throw new Error('FRED returned no observations');
      return out;
    },
    {
      source: 'FRED',
      ttlMs: MACRO_REFRESH_MS.fred_rates,
      refreshPolicy: '1-2x daily',
      toObservations: (payload) => payload.map((item) => ({
        label: item.label,
        valueNumeric: item.value,
        direction: item.direction,
        valueText: item.date,
      })),
    },
  );
}

async function loadAlphaVantageCommodities() {
  const apiKey = (process.env.ALPHAVANTAGE_API_KEY || '').trim();
  if (!apiKey) {
    const cached = await getCachedDataset('alphavantage_commodities');
    if (cached?.payload) {
      return { ...cached, fromCache: true, refreshed: false, stale: !isFresh(cached) };
    }
    return {
      datasetKey: 'alphavantage_commodities',
      payload: { commodities: [] },
      source: 'unavailable',
      fetchedAt: null,
      expiresAt: null,
      stale: true,
      fromCache: false,
      refreshed: false,
      meta: { reason: 'ALPHAVANTAGE_API_KEY not configured' },
    };
  }

  return getOrFetchDataset(
    'alphavantage_commodities',
    async () => {
      const get = async (params) => {
        const qs = new URLSearchParams({ ...params, apikey: apiKey });
        return fetchJson(`https://www.alphavantage.co/query?${qs}`);
      };
      const commodities = [];

      const gold = await get({ function: 'GOLD_SILVER_SPOT', symbol: 'GOLD' });
      if (gold?.Information || gold?.Note) throw new Error(gold.Information || gold.Note);
      if (gold?.price) {
        commodities.push({
          name: 'Gold',
          direction: 'Firming',
          implication: 'Gold remains a macro hedge input. Firm gold prices often coincide with elevated policy or geopolitical uncertainty.',
          source: 'Alpha Vantage',
        });
      }

      const wti = await get({ function: 'WTI', interval: 'monthly' });
      if (wti?.Information || wti?.Note) throw new Error(wti.Information || wti.Note);
      if (Array.isArray(wti?.data) && wti.data[0]) {
        const latest = Number(wti.data[0].value);
        const previous = Number(wti.data[1]?.value);
        const direction = directionFromDelta(latest - previous, { up: 1, down: -1 });
        commodities.push({
          name: 'Crude Oil (WTI)',
          direction,
          implication: direction === 'Firming'
            ? 'Higher oil raises transportation and input-cost pressure, which can keep inflation stickier and delay policy easing.'
            : direction === 'Easing'
              ? 'Softer oil can ease inflation pressure and improve the policy backdrop for rate-sensitive demand.'
              : 'Oil remains a key inflation and current-account transmission channel for India.',
          source: 'Alpha Vantage',
          asOf: wti.data[0].date,
        });
      }

      if (!commodities.length) throw new Error('Alpha Vantage commodities empty');
      return { commodities };
    },
    {
      source: 'Alpha Vantage',
      ttlMs: MACRO_REFRESH_MS.alphavantage_commodities,
      refreshPolicy: '12h conserve quota',
      toObservations: (payload) => (payload.commodities || []).map((item) => ({
        label: item.name,
        direction: item.direction,
        valueText: item.asOf || null,
      })),
    },
  );
}

async function loadIndianApiCommodities() {
  return getOrFetchDataset(
    'indianapi_commodities',
    async () => {
      const context = await getMarketContext();
      if (context.unavailable && !(context.commodities || []).length) {
        throw new Error('IndianAPI commodities unavailable');
      }
      return {
        commodities: (context.commodities || []).map((item) => ({
          name: item.name,
          direction: toSentiment(item.trend),
          implication: `${item.name} is ${String(item.trend).toLowerCase()} in the latest Indian commodity feed, which feeds into inflation, margins and sector leadership.`,
          source: 'IndianAPI',
        })),
        headlines: context.headlines || [],
      };
    },
    {
      source: 'IndianAPI',
      ttlMs: MACRO_REFRESH_MS.indianapi_commodities,
      toObservations: (payload) => (payload.commodities || []).map((item) => ({
        label: item.name,
        direction: item.direction,
      })),
    },
  );
}

async function loadWeatherIndia() {
  return getOrFetchDataset(
    'weather_india',
    async () => {
      const [mumbai, delhi] = await Promise.all([
        fetchJson('https://api.open-meteo.com/v1/forecast?latitude=19.076&longitude=72.8777&daily=precipitation_sum,temperature_2m_max&timezone=Asia%2FKolkata&forecast_days=7'),
        fetchJson('https://api.open-meteo.com/v1/forecast?latitude=28.6139&longitude=77.209&daily=precipitation_sum,temperature_2m_max&timezone=Asia%2FKolkata&forecast_days=7'),
      ]);
      const rain = [...(mumbai.daily?.precipitation_sum || []), ...(delhi.daily?.precipitation_sum || [])]
        .map(Number)
        .filter(Number.isFinite);
      const heat = [...(mumbai.daily?.temperature_2m_max || []), ...(delhi.daily?.temperature_2m_max || [])]
        .map(Number)
        .filter(Number.isFinite);
      const rainTotal = rain.reduce((a, b) => a + b, 0);
      const maxHeat = heat.length ? Math.max(...heat) : null;
      return {
        region: 'India (Mumbai/Delhi proxy)',
        rainfallOutlook: rainTotal >= 40 ? 'Wet' : rainTotal >= 10 ? 'Mixed' : 'Dry',
        heatStress: maxHeat != null && maxHeat >= 38 ? 'Elevated' : 'Moderate',
        implication: rainTotal < 10
          ? 'Weak near-term rainfall raises food-inflation and rural-income monitoring risks.'
          : 'Near-term rainfall support reduces immediate agricultural stress, though local anomalies can still matter for food prices.',
        source: 'Open-Meteo',
      };
    },
    {
      source: 'Open-Meteo',
      ttlMs: MACRO_REFRESH_MS.weather_india,
      refreshPolicy: '6-12h',
      toObservations: (payload) => [{
        label: 'India rainfall outlook',
        valueText: payload.rainfallOutlook,
        direction: payload.rainfallOutlook,
      }],
    },
  );
}

function buildCountryCards({ fred, worldBank, commodities }) {
  const usRates = (fred || []).find((item) => /federal funds|10y/i.test(item.label));
  const indiaInflation = (worldBank || []).find((item) => /cpi inflation/i.test(item.label));
  const indiaGrowth = (worldBank || []).find((item) => /gdp growth/i.test(item.label));
  const oil = (commodities || []).find((item) => /oil|crude/i.test(item.name));

  return [
    {
      name: 'India',
      condition: indiaGrowth?.direction === 'Firming' ? 'Improving' : indiaInflation?.direction === 'Firming' ? 'Stable' : 'Stable',
      why: `Domestic growth and inflation remain the core policy constraint. ${indiaGrowth ? `Growth evidence is ${String(indiaGrowth.direction).toLowerCase()}.` : ''} ${indiaInflation ? `Inflation evidence is ${String(indiaInflation.direction).toLowerCase()}.` : ''} Oil and currency transmission continue to shape the RBI policy room.`,
    },
    {
      name: 'United States',
      condition: usRates?.direction === 'Easing' ? 'Improving' : usRates?.direction === 'Firming' ? 'Weakening' : 'Stable',
      why: usRates
        ? `US rate conditions are ${String(usRates.direction).toLowerCase()}, which matters for global liquidity, the dollar and equity risk appetite.`
        : 'US policy remains the dominant global financial-conditions driver for emerging markets including India.',
    },
    {
      name: 'China',
      condition: 'Stable',
      why: 'China remains a demand and metals-pricing force for India through trade, commodities and global manufacturing cycles.',
    },
    {
      name: 'Europe',
      condition: 'Stable',
      why: 'Euro-area growth and policy affect global risk sentiment and export demand for Indian manufacturing and services.',
    },
    {
      name: 'Japan',
      condition: 'Stable',
      why: 'Japanese policy and yen moves remain a secondary but relevant signal for global carry and risk appetite.',
    },
    {
      name: 'Middle East',
      condition: oil?.direction === 'Firming' ? 'Weakening' : 'Stable',
      why: oil?.direction === 'Firming'
        ? 'Energy-supply geopolitics raise oil-linked inflation and current-account sensitivity for India.'
        : 'Energy geopolitics remain a latent inflation and shipping-risk channel.',
    },
  ];
}

function datasetMeta(record) {
  return {
    key: record.datasetKey,
    source: record.source,
    fetchedAt: record.fetchedAt,
    expiresAt: record.expiresAt,
    stale: Boolean(record.stale),
    fromCache: Boolean(record.fromCache),
    refreshed: Boolean(record.refreshed),
    upstreamError: record.upstreamError || null,
  };
}

export async function getMacroContext({ force = false } = {}) {
  if (!force && assembled && assembledExpiresAt > Date.now()) return assembled;
  if (inflight) return inflight;

  inflight = (async () => {
    const [fxRec, worldBankRec, fredRec, alphaRec, indianRec, weatherRec] = await Promise.all([
      loadUsdInr(),
      loadWorldBankIndia(),
      loadFredRates(),
      loadAlphaVantageCommodities(),
      loadIndianApiCommodities(),
      loadWeatherIndia(),
    ]);

    const alphaCommodities = alphaRec.payload?.commodities || [];
    const indianCommodities = indianRec.payload?.commodities || [];
    const commodities = [...alphaCommodities, ...indianCommodities]
      .filter((item, index, arr) => arr.findIndex((x) => x.name === item.name) === index)
      .slice(0, 8);

    const datasetStatus = [fxRec, worldBankRec, fredRec, alphaRec, indianRec, weatherRec].map(datasetMeta);
    const sourcesUsed = [...new Set(datasetStatus
      .filter((item) => item.source && item.source !== 'unavailable' && item.fetchedAt)
      .map((item) => item.source))];

    const missingSources = [
      !(process.env.FRED_API_KEY || '').trim() ? 'FRED_API_KEY' : null,
      !(process.env.FINNHUB_API_KEY || '').trim() ? 'FINNHUB_API_KEY' : null,
      !(process.env.TWELVE_DATA_API_KEY || '').trim() ? 'TWELVE_DATA_API_KEY' : null,
      !(process.env.POLYGON_API_KEY || '').trim() ? 'POLYGON_API_KEY' : null,
      !(process.env.FMP_API_KEY || '').trim() ? 'FMP_API_KEY' : null,
      !(process.env.RBI_DATA_API_KEY || '').trim() ? 'RBI Data API' : null,
    ].filter(Boolean);

    const worldBank = worldBankRec.payload || [];
    const fred = fredRec.payload || [];
    const fxPayload = fxRec.payload;
    const fx = fxPayload ? [fxPayload] : [{
      pair: 'USD/INR',
      direction: 'Stable',
      implication: 'Currency evidence is limited in this refresh; AGI treats dollar transmission as a monitored input rather than a firm conclusion.',
      source: 'unavailable',
    }];

    const weather = weatherRec.payload || {
      region: 'India',
      rainfallOutlook: 'Unavailable',
      heatStress: 'Unavailable',
      implication: 'Weather evidence is missing; monsoon transmission into food inflation remains a monitored risk.',
      source: 'unavailable',
    };

    const value = {
      updatedAt: new Date().toISOString(),
      cachePolicy: MACRO_REFRESH_MS,
      datasetStatus,
      // Stale means we are serving past-TTL cached evidence — not “optional source missing”.
      stale: datasetStatus.some((item) => item.stale && item.fromCache && item.fetchedAt),
      fx,
      worldBank,
      fred,
      commodities,
      weather,
      headlines: indianRec.payload?.headlines || [],
      countries: buildCountryCards({ fred, worldBank, commodities }),
      sourcesUsed,
      missingSources,
      lastSuccessfulFetches: datasetStatus
        .filter((item) => item.fetchedAt)
        .map((item) => ({ key: item.key, fetchedAt: item.fetchedAt, source: item.source, stale: item.stale })),
    };

    assembled = value;
    assembledExpiresAt = Date.now() + ASSEMBLED_CACHE_MS;
    return value;
  })().finally(() => {
    inflight = null;
  });

  return inflight;
}
