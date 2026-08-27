export const LIVE_TAG = 'live';
export const LIVE_POLL_MS = 40000;

export const ARTICLE_CARD_SELECT =
  'id, title, slug, excerpt, cover_url, tags, published_at, section, status';
export const LIVE_ARTICLE_COLUMNS =
  'is_live, live_updates, live_started_at, live_ended_at, updated_at';
export const ARTICLE_CARD_SELECT_WITH_LIVE = `${ARTICLE_CARD_SELECT}, ${LIVE_ARTICLE_COLUMNS}`;

export function hasLiveTag(tags) {
  if (!Array.isArray(tags)) return false;
  return tags.some((tag) => String(tag || '').trim().toLowerCase() === LIVE_TAG);
}

export function withLiveTag(tags, enabled) {
  const next = (Array.isArray(tags) ? tags : []).filter(
    (tag) => String(tag || '').trim().toLowerCase() !== LIVE_TAG
  );
  if (enabled) next.push(LIVE_TAG);
  return Array.from(new Set(next));
}

export function isLiveArticle(article) {
  if (!article) return false;
  if (article.live_ended_at || article.liveEndedAt) return false;
  if (article.is_live === true || article.isLive === true) return true;
  if (article.is_live === false || article.isLive === false) return false;
  return hasLiveTag(article.tags);
}

export function isMissingLiveColumnError(error) {
  const msg = `${error?.message || ''} ${error?.details || ''} ${error?.hint || ''}`;
  return /is_live|live_updates|live_started_at|live_ended_at/i.test(msg);
}

export function normalizeLiveUpdates(value) {
  let raw = value;
  if (typeof raw === 'string') {
    try {
      raw = JSON.parse(raw);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item, index) => {
      if (!item || typeof item !== 'object') return null;
      const at = item.at || item.published_at || item.created_at || null;
      const date = at ? new Date(at) : null;
      const iso = date && !Number.isNaN(date.getTime()) ? date.toISOString() : null;
      const html = String(item.html || item.body || item.content || '').trim();
      const headline = String(item.headline || item.title || '').trim();
      if (!html && !headline) return null;
      return {
        id: String(item.id || `update-${iso || index}`),
        at: iso,
        headline,
        html,
      };
    })
    .filter(Boolean)
    .sort((a, b) => {
      const ta = a.at ? Date.parse(a.at) : 0;
      const tb = b.at ? Date.parse(b.at) : 0;
      return tb - ta;
    });
}

export function latestLiveTimestamp(article) {
  const updates = normalizeLiveUpdates(article?.live_updates || article?.liveUpdates);
  const candidates = [
    updates[0]?.at,
    article?.updated_at,
    article?.updatedAt,
    article?.live_started_at,
    article?.liveStartedAt,
    article?.published_at,
    article?.publishedAt,
  ];
  let best = null;
  let bestMs = Number.NEGATIVE_INFINITY;
  for (const value of candidates) {
    if (!value) continue;
    const ms = Date.parse(value);
    if (Number.isNaN(ms) || ms <= bestMs) continue;
    bestMs = ms;
    best = new Date(ms).toISOString();
  }
  return best;
}

export function formatLiveClock(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const formatted = date.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata',
    day: 'numeric',
    month: 'short',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
  return `${formatted} IST`;
}

export function escapeHtml(value = '') {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function plaintextToHtml(text) {
  const raw = String(text || '').trim();
  if (!raw) return '';
  return raw
    .split(/\n{2,}/)
    .map((para) => `<p>${escapeHtml(para).replace(/\n/g, '<br />')}</p>`)
    .join('');
}

export function createLiveUpdate({ headline = '', html = '', body = '', at, id } = {}) {
  const resolvedHtml = String(html || '').trim() || plaintextToHtml(body);
  const resolvedHeadline = String(headline || '').trim();
  const when = at ? new Date(at) : new Date();
  const iso = Number.isNaN(when.getTime()) ? new Date().toISOString() : when.toISOString();
  return {
    id:
      id ||
      (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `u-${Date.parse(iso)}`),
    at: iso,
    headline: resolvedHeadline,
    html: resolvedHtml,
  };
}

export async function queryArticlesSelectingLive(makeQuery) {
  const withLive = await makeQuery(ARTICLE_CARD_SELECT_WITH_LIVE);
  if (withLive?.error && isMissingLiveColumnError(withLive.error)) {
    return makeQuery(ARTICLE_CARD_SELECT);
  }
  return withLive;
}
