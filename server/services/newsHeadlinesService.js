/**
 * Public-safe headline feed.
 * Only title, source, timestamp and outbound URL are returned; article body
 * and images remain with the originating publisher.
 */

const NEWS_API_URL = 'https://newsapi.org/v2/top-headlines';
const NEWS_TTL_MS = 30 * 60 * 1000;
let cache = null;
let expiresAt = 0;
let inflight = null;

function fallback() {
  return {
    items: [],
    source: 'unavailable',
    updatedAt: new Date().toISOString(),
    stale: true,
  };
}

export async function getNewsHeadlines() {
  if (cache && Date.now() < expiresAt) return cache;
  if (inflight) return inflight;

  const apiKey = (process.env.NEWSAPI_KEY || '').trim();
  if (!apiKey) return fallback();

  inflight = (async () => {
    try {
      const url = new URL(NEWS_API_URL);
      url.searchParams.set('country', 'in');
      url.searchParams.set('category', 'business');
      url.searchParams.set('pageSize', '12');

      const response = await fetch(url, {
        headers: {
          Accept: 'application/json',
          'X-Api-Key': apiKey,
        },
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok || body.status !== 'ok') {
        throw new Error(body?.message || `News API request failed (${response.status})`);
      }

      cache = {
        items: (body.articles || [])
          .filter((article) => article?.title && article?.url)
          .map((article) => ({
            title: article.title,
            source: article.source?.name || 'News source',
            url: article.url,
            publishedAt: article.publishedAt || null,
          })),
        source: 'newsapi',
        updatedAt: new Date().toISOString(),
        stale: false,
      };
      expiresAt = Date.now() + NEWS_TTL_MS;
      return cache;
    } catch (error) {
      console.warn('[news-headlines]', error.message);
      return cache ? { ...cache, stale: true } : fallback();
    } finally {
      inflight = null;
    }
  })();

  return inflight;
}
