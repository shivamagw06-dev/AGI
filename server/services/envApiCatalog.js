/**
 * Soft catalogue of .env external APIs for Mission Control.
 * Never returns secret values — only configured / probed status.
 */

import { isGrowwConfigured } from '../providers/groww.js';
import { isUpstoxConfigured } from '../providers/upstox.js';
import { getGrowwHealth } from './growwHealth.js';
import { getUpstoxHealth } from './upstoxHealth.js';

function present(...keys) {
  return keys.some((k) => Boolean(String(process.env[k] || '').trim()));
}

/** Static catalogue of APIs declared across root / server / intelligence-engine .env examples. */
export function listEnvApiCatalog() {
  return [
    {
      name: 'Groww',
      env: ['GROWW_ACCESS_TOKEN', 'GROWW_API_KEY', 'GROWW_API_SECRET', 'GROWW_API_BASE'],
      configured: isGrowwConfigured(),
      role: 'Primary India market data (LTP / quote / OHLC / historical)',
    },
    {
      name: 'Upstox',
      env: [
        'UPSTOX_ACCESS_TOKEN',
        'UPSTOX_API',
        'UPSTOX_API_KEY',
        'UPSTOX_API_SECRET',
        'UPSTOX_REDIRECT_URI',
      ],
      configured: isUpstoxConfigured() || present('UPSTOX_API_KEY', 'UPSTOX_API', 'UPSTOX_CLIENT_ID'),
      role: 'Fundamentals / corporate actions (Bearer access token)',
    },
    {
      name: 'Indian API',
      env: ['INDIANAPI_KEY', 'INDIAN_API_KEY', 'INDIANAPI_BASE', 'INDIAN_API_BASE_URL'],
      configured: present('INDIANAPI_KEY', 'INDIAN_API_KEY', 'VITE_INDIANAPI_KEY'),
      role: 'Market data provider (Node + intelligence-engine)',
    },
    {
      name: 'Finnhub',
      env: ['FINNHUB_API_KEY', 'FINNHUB_BASE_URL'],
      configured: present('FINNHUB_API_KEY'),
      role: 'Market / macro data',
    },
    {
      name: 'FMP',
      env: ['FMP_API_KEY', 'FMP_BASE_URL'],
      configured: present('FMP_API_KEY'),
      role: 'Fundamentals / market data',
    },
    {
      name: 'Yahoo Finance',
      env: ['YAHOO_PROVIDER'],
      configured: process.env.YAHOO_PROVIDER !== 'false',
      role: 'Secondary MarketData adapter (no API key)',
    },
    {
      name: 'Alpha Vantage',
      env: ['ALPHAVANTAGE_API_KEY'],
      configured: present('ALPHAVANTAGE_API_KEY'),
      role: 'Macro intelligence',
    },
    {
      name: 'FRED',
      env: ['FRED_API_KEY'],
      configured: present('FRED_API_KEY'),
      role: 'Macro / rates series',
    },
    {
      name: 'Twelve Data',
      env: ['TWELVE_DATA_API_KEY'],
      configured: present('TWELVE_DATA_API_KEY'),
      role: 'Market / macro series',
    },
    {
      name: 'Polygon',
      env: ['POLYGON_API_KEY'],
      configured: present('POLYGON_API_KEY'),
      role: 'Market data',
    },
    {
      name: 'NewsAPI',
      env: ['NEWSAPI_KEY'],
      configured: present('NEWSAPI_KEY'),
      role: 'News headlines',
    },
    {
      name: 'Perplexity',
      env: ['PERPLEXITY_KEY', 'PERPLEXITY_API_KEY'],
      configured: present('PERPLEXITY_KEY', 'PERPLEXITY_API_KEY', 'VITE_PERPLEXITY_KEY'),
      role: 'Research / narrative assist',
    },
    {
      name: 'OpenAI',
      env: ['OPENAI_API_KEY', 'OPENAI_MARKET_BRIEFING_MODEL'],
      configured: present('OPENAI_API_KEY'),
      role: 'Optional market briefing narrative',
    },
    {
      name: 'Supabase',
      env: ['SUPABASE_URL', 'SUPABASE_SERVICE_ROLE_KEY', 'VITE_SUPABASE_URL', 'VITE_SUPABASE_ANON_KEY'],
      configured: present('SUPABASE_URL', 'VITE_SUPABASE_URL'),
      role: 'Auth / research publish / storage',
    },
    {
      name: 'Resend',
      env: ['RESEND_API_KEY', 'FROM_EMAIL', 'NEWSLETTER_FROM_EMAIL'],
      configured: present('RESEND_API_KEY'),
      role: 'Auth + newsletter email',
    },
    {
      name: 'SendGrid',
      env: ['SENDGRID_API_KEY'],
      configured: present('SENDGRID_API_KEY'),
      role: 'Optional email transport',
    },
    {
      name: 'RBI Data',
      env: ['RBI_DATA_API_KEY'],
      configured: present('RBI_DATA_API_KEY'),
      role: 'Optional macro / FX authenticated endpoints',
    },
    {
      name: 'ExchangeRate',
      env: ['EXCHANGERATE_API_KEY'],
      configured: present('EXCHANGERATE_API_KEY'),
      role: 'Optional FX rates',
    },
    {
      name: 'Intelligence Engine',
      env: ['INTELLIGENCE_ENGINE_URL', 'INTELLIGENCE_ENGINE_TOKEN'],
      configured: present('INTELLIGENCE_ENGINE_URL'),
      role: 'Python FastAPI AGI engine',
    },
  ];
}

function upsertApiStatus(apis, entry) {
  const list = Array.isArray(apis) ? [...apis] : [];
  const idx = list.findIndex((a) => String(a?.name || '').toLowerCase() === entry.name.toLowerCase());
  if (idx >= 0) {
    list[idx] = { ...list[idx], ...entry };
  } else {
    list.unshift(entry);
  }
  return list;
}

/**
 * Probe Groww + merge .env API catalogue into Mission Control api_status.
 * Soft-wire only — never blocks the cockpit.
 */
export async function enrichMissionControlApis(desk = {}) {
  const out = desk && typeof desk === 'object' ? { ...desk } : {};
  let apis = Array.isArray(out.api_status) ? [...out.api_status] : [];
  const catalog = listEnvApiCatalog();

  // Live Groww probe (no secrets in payload)
  let groww = null;
  try {
    groww = await getGrowwHealth();
  } catch (err) {
    groww = {
      ok: false,
      configured: isGrowwConfigured(),
      message: err?.message || 'Groww probe failed',
      tests: [],
    };
  }

  const growwStatus = !groww?.configured
    ? 'Offline'
    : groww.ok
      ? 'Healthy'
      : groww.passed > 0
        ? 'Warning'
        : 'Critical';
  const growwColour =
    growwStatus === 'Healthy' ? 'Green' : growwStatus === 'Warning' ? 'Yellow' : 'Red';

  apis = upsertApiStatus(apis, {
    name: 'Groww',
    status: growwStatus,
    colour: growwColour,
    provider_confidence: groww?.configured ? 'configured' : 'missing_env',
    last_error: groww?.ok ? null : groww?.message || groww?.tests?.find((t) => !t.ok)?.error || null,
    note: groww?.configured
      ? `Auth: ${groww.authMode || 'unknown'}; probes ${groww.passed ?? 0}/${groww.total ?? 0}`
      : 'Set GROWW_ACCESS_TOKEN (daily) or GROWW_API_KEY + GROWW_API_SECRET',
    capabilities: ['ltp', 'quote', 'ohlc', 'historical'],
    env_keys: ['GROWW_ACCESS_TOKEN', 'GROWW_API_KEY', 'GROWW_API_SECRET'],
    checked_at: groww?.checkedAt || new Date().toISOString(),
  });

  // Soft fill remaining catalogue entries when missing from IOC list
  const known = new Set(apis.map((a) => String(a?.name || '').toLowerCase()));
  for (const item of catalog) {
    if (item.name === 'Groww') continue;
    if (known.has(item.name.toLowerCase())) {
      // Enrich configured flag when we know env presence
      const idx = apis.findIndex((a) => String(a?.name || '').toLowerCase() === item.name.toLowerCase());
      if (idx >= 0 && apis[idx].provider_confidence === 'not_probed') {
        apis[idx] = {
          ...apis[idx],
          provider_confidence: item.configured ? 'configured' : 'missing_env',
          status: item.configured ? apis[idx].status || 'Unknown' : 'Offline',
          colour: item.configured ? apis[idx].colour || 'Yellow' : 'Red',
          note: item.role,
          env_keys: item.env,
        };
      }
      continue;
    }
    apis.push({
      name: item.name,
      status: item.configured ? 'Unknown' : 'Offline',
      colour: item.configured ? 'Yellow' : 'Red',
      provider_confidence: item.configured ? 'configured' : 'missing_env',
      last_error: item.configured ? null : `Missing env: ${item.env.join(' / ')}`,
      note: item.role,
      env_keys: item.env,
    });
    known.add(item.name.toLowerCase());
  }

  out.api_status = apis;
  out.env_api_catalog = catalog.map((c) => ({
    name: c.name,
    configured: c.configured,
    role: c.role,
    env_keys: c.env,
  }));
  out.groww_health = {
    configured: Boolean(groww?.configured),
    ok: Boolean(groww?.ok),
    authMode: groww?.authMode || null,
    passed: groww?.passed ?? 0,
    total: groww?.total ?? 0,
    message: groww?.message || null,
    tests: (groww?.tests || []).map((t) => ({
      name: t.name,
      ok: Boolean(t.ok),
      error: t.ok ? undefined : t.error,
    })),
    checkedAt: groww?.checkedAt || new Date().toISOString(),
  };

  let upstox = null;
  try {
    upstox = await getUpstoxHealth();
  } catch (err) {
    upstox = {
      ok: false,
      configured: isUpstoxConfigured(),
      message: err?.message || 'Upstox probe failed',
    };
  }
  const upstoxStatus = !upstox?.configured
    ? 'Offline'
    : upstox.ok
      ? 'Healthy'
      : 'Critical';
  apis = upsertApiStatus(apis, {
    name: 'Upstox',
    status: upstoxStatus,
    colour: upstoxStatus === 'Healthy' ? 'Green' : upstoxStatus === 'Offline' ? 'Red' : 'Yellow',
    provider_confidence: upstox?.configured ? 'configured' : 'missing_env',
    last_error: upstox?.ok ? null : upstox?.message || null,
    note: upstox?.configured
      ? upstox.message || `Auth source: ${upstox.authSource || 'token'}`
      : 'Set UPSTOX_ACCESS_TOKEN (Bearer). UPSTOX_API key alone is not enough.',
    capabilities: ['corporate_actions', 'fundamentals'],
    env_keys: ['UPSTOX_ACCESS_TOKEN', 'UPSTOX_API', 'UPSTOX_API_KEY', 'UPSTOX_API_SECRET'],
    checked_at: upstox?.checkedAt || new Date().toISOString(),
  });
  out.upstox_health = {
    configured: Boolean(upstox?.configured),
    ok: Boolean(upstox?.ok),
    authSource: upstox?.authSource || null,
    message: upstox?.message || null,
    isin: upstox?.isin || null,
    event_count: upstox?.corporate_actions?.count ?? null,
    checkedAt: upstox?.checkedAt || new Date().toISOString(),
  };
  return out;
}
