import { createSupabaseAdmin } from '../lib/supabaseAdmin.js';

const TABLE = 'live_desk_broadcasts';
const VIDEO_ID = /^[A-Za-z0-9_-]{11}$/;

const DEFINITIONS = Object.freeze({
  global: Object.freeze({
    id: 'global', market: 'GLOBAL', title: 'Bloomberg Live', provider: 'Bloomberg',
    attribution: 'Source: Bloomberg / YouTube', videoId: 'QB5BNdBFujE',
  }),
  india: Object.freeze({
    id: 'india', market: 'INDIA', title: 'NDTV Profit Live', provider: 'NDTV Profit',
    attribution: 'Source: NDTV Profit / YouTube', videoId: 'EN-N1xhtBqU',
  }),
});

function failure(message, status = 400) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function allowedYoutubeHost(hostname) {
  const host = String(hostname || '').toLowerCase().replace(/^www\./, '').replace(/^m\./, '');
  return host === 'youtube.com' || host === 'youtu.be' || host === 'youtube-nocookie.com';
}

function candidateId(url) {
  const host = url.hostname.toLowerCase().replace(/^www\./, '').replace(/^m\./, '');
  if (host === 'youtu.be') return url.pathname.split('/').filter(Boolean)[0] || '';
  if (url.pathname === '/watch') return url.searchParams.get('v') || '';
  const parts = url.pathname.split('/').filter(Boolean);
  if (['embed', 'shorts', 'live'].includes(parts[0])) return parts[1] || '';
  return '';
}

export function normalizeYoutubeVideoUrl(input) {
  const value = String(input || '').trim();
  if (VIDEO_ID.test(value)) return value;
  let url;
  try { url = new URL(value); } catch { throw failure('Paste a valid YouTube URL.'); }
  if (url.protocol !== 'https:' || !allowedYoutubeHost(url.hostname)) {
    throw failure('Only official HTTPS YouTube links are accepted.');
  }
  const id = candidateId(url);
  if (!VIDEO_ID.test(id)) {
    throw failure('This link does not identify a YouTube video. Paste the watch link or the channel /live link.');
  }
  return id;
}

function isChannelLiveUrl(input) {
  try {
    const url = new URL(String(input || '').trim());
    return allowedYoutubeHost(url.hostname) && /\/(channel\/[^/]+|@[^/]+)\/live\/?$/.test(url.pathname);
  } catch { return false; }
}

export async function resolveYoutubeVideoUrl(input, fetchImpl = globalThis.fetch) {
  if (!isChannelLiveUrl(input)) return normalizeYoutubeVideoUrl(input);
  if (typeof fetchImpl !== 'function') throw failure('YouTube resolver is unavailable.', 503);
  const response = await fetchImpl(String(input).trim(), {
    redirect: 'follow',
    headers: { 'User-Agent': 'Mozilla/5.0 AGI-Live-Desk/1.0' },
    signal: AbortSignal.timeout(12_000),
  });
  if (!response.ok) throw failure(`YouTube returned HTTP ${response.status}.`, 502);
  return normalizeYoutubeVideoUrl(response.url);
}

function toBroadcast(definition, row = {}) {
  const videoId = VIDEO_ID.test(String(row.video_id || '')) ? row.video_id : definition.videoId;
  return {
    id: definition.id,
    market: definition.market,
    title: definition.title,
    provider: definition.provider,
    attribution: definition.attribution,
    videoId,
    youtubeUrl: `https://www.youtube.com/watch?v=${videoId}`,
    embedUrl: `https://www.youtube.com/embed/${videoId}`,
    updatedAt: row.updated_at || null,
  };
}

export function defaultLiveDeskBroadcasts() {
  return Object.values(DEFINITIONS).map((definition) => toBroadcast(definition));
}

export async function getLiveDeskBroadcasts() {
  const db = createSupabaseAdmin();
  if (!db) return { ok: true, broadcasts: defaultLiveDeskBroadcasts(), storage: 'defaults' };
  const { data, error } = await db.from(TABLE).select('id,video_id,updated_at');
  if (error) {
    console.warn('[live-desk-broadcasts] using defaults:', error.message);
    return { ok: true, broadcasts: defaultLiveDeskBroadcasts(), storage: 'defaults' };
  }
  const rows = new Map((data || []).map((row) => [row.id, row]));
  return {
    ok: true,
    broadcasts: Object.values(DEFINITIONS).map((definition) => toBroadcast(definition, rows.get(definition.id))),
    storage: 'supabase',
  };
}

export async function saveLiveDeskBroadcast({ id, youtubeUrl, actor }) {
  const definition = DEFINITIONS[id];
  if (!definition) throw failure('Unknown broadcast slot.');
  const videoId = await resolveYoutubeVideoUrl(youtubeUrl);
  const db = createSupabaseAdmin();
  if (!db) throw failure('Broadcast storage is not configured.', 503);
  const row = {
    id,
    video_id: videoId,
    youtube_url: `https://www.youtube.com/watch?v=${videoId}`,
    updated_by: actor?.id || null,
    updated_at: new Date().toISOString(),
  };
  const { data, error } = await db.from(TABLE).upsert(row, { onConflict: 'id' }).select('id,video_id,updated_at').single();
  if (error) throw failure(`Could not save broadcast link: ${error.message}`, 503);
  return { ok: true, broadcast: toBroadcast(definition, data) };
}
