const CACHE_MS = 30 * 60 * 1000;
const MAX_NEWS = 10;
const MAX_COMMODITIES = 12;

let cache = null;
let expiresAt = 0;
let inflight = null;

function firstArray(value, visited = new Set()) {
  if (!value || typeof value !== 'object' || visited.has(value)) return [];
  visited.add(value);
  if (Array.isArray(value)) return value;
  for (const child of Object.values(value)) {
    const result = firstArray(child, visited);
    if (result.length) return result;
  }
  return [];
}

function text(value) {
  return typeof value === 'string' && value.trim() ? value.trim() : null;
}

function trendLabel(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || Math.abs(number) < 0.05) return 'Stable';
  return number > 0 ? 'Firming' : 'Easing';
}

function normalizeNews(payload) {
  return firstArray(payload)
    .map((item) => ({
      title: text(item.title || item.headline || item.news_title || item.name),
      source: text(item.source || item.publisher || item.provider) || 'IndianAPI',
      url: text(item.url || item.link || item.news_url),
      publishedAt: text(item.published_at || item.publishedAt || item.date || item.datetime),
    }))
    .filter((item) => item.title)
    .slice(0, MAX_NEWS);
}

function normalizeCommodities(payload) {
  return firstArray(payload)
    .map((item) => ({
      name: text(item.name || item.commodity || item.product || item.symbol || item.display_name),
      trend: trendLabel(item.percent_change ?? item.per_change ?? item.change_percent ?? item.change ?? item.net_change),
      updatedAt: text(item.updated_at || item.updatedAt || item.messageTime || item.timestamp || item.date),
    }))
    .filter((item) => item.name)
    .slice(0, MAX_COMMODITIES);
}

function unavailable() {
  return {
    headlines: [],
    commodities: [],
    source: 'IndianAPI',
    updatedAt: new Date().toISOString(),
    unavailable: true,
  };
}

export async function getMarketContext() {
  if (cache && expiresAt > Date.now()) return cache;
  if (inflight) return inflight;

  inflight = (async () => {
    try {
      const apiKey = (process.env.INDIANAPI_KEY || process.env.VITE_INDIANAPI_KEY || '').trim();
      const baseUrl = (process.env.INDIANAPI_BASE || 'https://stock.indianapi.in').replace(/\/$/, '');
      if (!apiKey) throw new Error('IndianAPI key is not configured');
      const get = async (path) => {
        const response = await fetch(`${baseUrl}${path}`, { headers: { Accept: 'application/json', 'x-api-key': apiKey } });
        if (!response.ok) throw new Error(`${path} failed (${response.status})`);
        return response.json();
      };
      const [news, commodities] = await Promise.allSettled([get('/news'), get('/commodities')]);
      const value = {
        headlines: news.status === 'fulfilled' ? normalizeNews(news.value) : [],
        commodities: commodities.status === 'fulfilled' ? normalizeCommodities(commodities.value) : [],
        source: 'IndianAPI',
        updatedAt: new Date().toISOString(),
        unavailable: news.status === 'rejected' && commodities.status === 'rejected',
      };
      cache = value;
      expiresAt = Date.now() + CACHE_MS;
      return value;
    } catch (error) {
      console.warn('[market-context]', error.message);
      return cache || unavailable();
    } finally {
      inflight = null;
    }
  })();
  return inflight;
}
