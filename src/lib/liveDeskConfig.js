/**
 * Live Desk configuration.
 *
 * The stream is Bloomberg's own public YouTube broadcast, embedded with the
 * standard YouTube player. AGI does not host, proxy, record or restream it,
 * and the player keeps Bloomberg's and YouTube's branding intact.
 */

// A channel live_stream URL rather than a video id.
//
// Bloomberg starts a new video for each broadcast, so a hardcoded id goes dead
// the next time they restart the stream and the page would show "video
// unavailable" until someone noticed. The channel form resolves to whatever
// that channel is currently airing, so it survives a restart.
//
// This is a public URL, not a secret. It is configurable because the channel
// may change and a redeploy should not be required to follow it.
const DEFAULT_BLOOMBERG_LIVE_URL =
  'https://www.youtube.com/embed/live_stream?channel=UCIALMKvObZNtJ6AmdCLP7Lg';

// The app is Vite, not Next, so the public prefix is VITE_ rather than
// NEXT_PUBLIC_.
const configured = String(import.meta?.env?.VITE_BLOOMBERG_LIVE_URL || '').trim();

/** Accepts a full embed URL or a bare YouTube video id. */
function toEmbedUrl(value) {
  if (!value) return DEFAULT_BLOOMBERG_LIVE_URL;
  if (/^https?:\/\//i.test(value)) return value;
  if (/^[\w-]{6,}$/.test(value)) return `https://www.youtube.com/embed/${value}`;
  return DEFAULT_BLOOMBERG_LIVE_URL;
}

export const BLOOMBERG_LIVE_EMBED_URL = toEmbedUrl(configured);

/** Where "Watch on YouTube" points. */
export const BLOOMBERG_LIVE_WATCH_URL = (() => {
  try {
    const url = new URL(BLOOMBERG_LIVE_EMBED_URL);
    const channel = url.searchParams.get('channel');
    if (channel) return `https://www.youtube.com/channel/${channel}/live`;
    const id = url.pathname.split('/').filter(Boolean).pop();
    return id && id !== 'live_stream' ? `https://www.youtube.com/watch?v=${id}` : 'https://www.youtube.com/@markets';
  } catch {
    return 'https://www.youtube.com/@markets';
  }
})();

export const BLOOMBERG_ATTRIBUTION = 'Bloomberg Live — Source: Bloomberg / YouTube';

/** Refresh cadences, in ms. Deliberately unequal: prices move continuously,
 *  the event calendar does not, and research changes on a publishing cycle. */
export const REFRESH_MS = Object.freeze({
  pulse: 45_000,
  intelligence: 60_000,
  events: 300_000,
  research: 900_000,
});
