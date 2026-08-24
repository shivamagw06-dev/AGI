/**
 * Live Desk configuration.
 *
 * Two public broadcasts, each in its publisher's own YouTube player: Bloomberg
 * for global markets, NDTV Profit for India. AGI does not host, proxy, record
 * or restream either, and neither player is modified - branding, controls and
 * YouTube's chrome are left as the publisher ships them.
 */

// Channel live_stream URLs rather than video ids.
//
// Both broadcasters start a new video for each session, so a hardcoded id dies
// at the next restart and the card would show "video unavailable" until
// somebody noticed. The channel form resolves to whatever that channel is
// currently airing.
//
// These are public URLs, not secrets. They are configurable because a channel
// can change and following it should not require a redeploy.
const DEFAULTS = {
  bloomberg: 'https://www.youtube.com/embed/live_stream?channel=UCIALMKvObZNtJ6AmdCLP7Lg',
  ndtvProfit: 'https://www.youtube.com/embed/live_stream?channel=UC5LBDdnEQUOtcccQTZ4LGSg',
};

// The app is Vite, not Next, so the public prefix is VITE_ rather than
// NEXT_PUBLIC_.
const env = (key) => String(import.meta?.env?.[key] || '').trim();

/** Accepts a full embed URL or a bare YouTube video id. */
function toEmbedUrl(value, fallback) {
  if (!value) return fallback;
  if (/^https?:\/\//i.test(value)) return value;
  if (/^[\w-]{6,}$/.test(value)) return `https://www.youtube.com/embed/${value}`;
  return fallback;
}

/** Where "Watch on YouTube" points, derived from whatever embed is configured. */
function toWatchUrl(embedUrl, channelFallback) {
  try {
    const url = new URL(embedUrl);
    const channel = url.searchParams.get('channel');
    if (channel) return `https://www.youtube.com/channel/${channel}/live`;
    const id = url.pathname.split('/').filter(Boolean).pop();
    return id && id !== 'live_stream' ? `https://www.youtube.com/watch?v=${id}` : channelFallback;
  } catch {
    return channelFallback;
  }
}

const bloombergEmbed = toEmbedUrl(
  env('VITE_BLOOMBERG_LIVE_URL') || env('VITE_BLOOMBERG_LIVE_YOUTUBE_ID'),
  DEFAULTS.bloomberg
);
const ndtvEmbed = toEmbedUrl(
  env('VITE_NDTV_PROFIT_LIVE_URL') || env('VITE_NDTV_PROFIT_LIVE_YOUTUBE_ID'),
  DEFAULTS.ndtvProfit
);

/**
 * The two broadcasts, described identically.
 *
 * One shape for both so the player component has no publisher-specific
 * branches: adding or replacing a broadcast is a config change, not a
 * component change.
 */
export const BROADCASTS = Object.freeze([
  Object.freeze({
    id: 'global',
    market: 'GLOBAL',
    title: 'Bloomberg Live',
    provider: 'Bloomberg',
    embedUrl: bloombergEmbed,
    externalUrl: toWatchUrl(bloombergEmbed, 'https://www.youtube.com/@markets'),
    attribution: 'Source: Bloomberg / YouTube',
  }),
  Object.freeze({
    id: 'india',
    market: 'INDIA',
    title: 'NDTV Profit Live',
    provider: 'NDTV Profit',
    embedUrl: ndtvEmbed,
    externalUrl: toWatchUrl(ndtvEmbed, 'https://www.youtube.com/@NDTVProfitIndia'),
    attribution: 'Source: NDTV Profit / YouTube',
  }),
]);

// Kept for callers that imported these before the desk became dual-screen.
export const BLOOMBERG_LIVE_EMBED_URL = bloombergEmbed;
export const BLOOMBERG_LIVE_WATCH_URL = BROADCASTS[0].externalUrl;
export const BLOOMBERG_ATTRIBUTION = 'Bloomberg Live — Source: Bloomberg / YouTube';

/** Refresh cadences, in ms. Deliberately unequal: prices move continuously,
 *  the event calendar does not, and research changes on a publishing cycle.
 *  No cadence here touches the players - see LiveBroadcastPlayer. */
export const REFRESH_MS = Object.freeze({
  pulse: 45_000,
  intelligence: 60_000,
  events: 300_000,
  research: 900_000,
});
