import { currencyStrength, fetchYahooFxIntelligence } from '../providers/yahooIndices.js';
import { fetchUpstoxGlobalFxQuotes } from '../providers/upstoxFx.js';

function returnPct(current, previous) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous === 0) return null;
  return ((current - previous) / previous) * 100;
}

function anchorFromReturn(current, percentReturn) {
  const price = Number(current);
  const move = Number(percentReturn);
  if (!Number.isFinite(price) || !Number.isFinite(move)) return null;
  const divisor = 1 + move / 100;
  return divisor > 0 ? price / divisor : null;
}

function overlayLatest(row, quote) {
  const oldPrice = Number(row?.price);
  const price = Number(quote?.price);
  if (!Number.isFinite(price) || price <= 0) return row;

  const d1Anchor = Number(quote.previousClose) || anchorFromReturn(oldPrice, row?.returns?.d1);
  const w1Anchor = anchorFromReturn(oldPrice, row?.returns?.w1);
  const m1Anchor = anchorFromReturn(oldPrice, row?.returns?.m1);
  const sparkline = Array.isArray(row?.sparkline) && row.sparkline.length
    ? [...row.sparkline.slice(0, -1), price]
    : [price];

  return {
    ...row,
    price,
    previousClose: Number.isFinite(Number(quote.previousClose)) ? Number(quote.previousClose) : null,
    asOf: quote.fetchedAt,
    low: Math.min(Number.isFinite(Number(row?.low)) ? Number(row.low) : price, price),
    high: Math.max(Number.isFinite(Number(row?.high)) ? Number(row.high) : price, price),
    returns: {
      d1: returnPct(price, d1Anchor),
      w1: returnPct(price, w1Anchor),
      m1: returnPct(price, m1Anchor),
    },
    sparkline,
    source: quote.source,
    historySource: row?.source || 'Yahoo Finance',
    latencySeconds: quote.latencySeconds,
    instrumentKey: quote.instrumentKey,
    quoteMode: '20-second delayed',
  };
}

export function mergeFxProviders(yahoo, upstox) {
  const quoteByTarget = new Map((upstox?.quotes || []).map((quote) => [`${quote.kind}:${quote.target}`, quote]));
  const pairs = (yahoo?.pairs || []).map((row) => {
    const quote = quoteByTarget.get(`pair:${row.pair}`);
    return quote ? overlayLatest(row, quote) : row;
  });
  const drivers = (yahoo?.drivers || []).map((row) => {
    const quote = quoteByTarget.get(`driver:${row.name}`);
    return quote ? overlayLatest(row, quote) : row;
  });
  const upstoxQuotes = upstox?.quotes?.length || 0;

  return {
    ...yahoo,
    pairs,
    drivers,
    strength: {
      d1: currencyStrength(pairs, 'd1'),
      w1: currencyStrength(pairs, 'w1'),
      m1: currencyStrength(pairs, 'm1'),
    },
    asOf: [...pairs, ...drivers].map((row) => row?.asOf).filter(Boolean).sort().at(-1) || yahoo?.asOf,
    source: upstoxQuotes
      ? 'Upstox 20-second indicators + Yahoo Finance history and global FX'
      : 'Yahoo Finance market reference (Upstox fallback)',
    providers: {
      yahoo: { ok: Boolean(yahoo?.pairs?.length), role: 'global FX and historical series' },
      upstox: {
        ok: Boolean(upstox?.ok && upstoxQuotes),
        configured: Boolean(upstox?.configured),
        quotes: upstoxQuotes,
        latencySeconds: upstox?.latencySeconds || 20,
        role: 'latest USD/INR and Brent reference',
        reason: upstox?.reason || null,
      },
    },
  };
}

export async function fetchFxIntelligence({
  force = false,
  yahooFetcher = fetchYahooFxIntelligence,
  upstoxFetcher = fetchUpstoxGlobalFxQuotes,
} = {}) {
  const yahoo = await yahooFetcher({ force });
  let upstox;
  try {
    upstox = await upstoxFetcher();
  } catch (error) {
    upstox = {
      ok: false,
      configured: true,
      quotes: [],
      reason: error?.status === 401 || error?.status === 403 ? 'authentication_failed' : 'upstream_unavailable',
    };
  }
  return mergeFxProviders(yahoo, upstox);
}
