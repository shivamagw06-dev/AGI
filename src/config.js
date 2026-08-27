// Resolves API origin for market-data proxy (Render in prod, localhost in dev).

const RENDER_API_ORIGIN = 'https://finance-news-backend-19i5.onrender.com';

function readViteApiUrl() {
  // Vite only inlines import.meta.env.VITE_* — avoid optional chaining on import.meta.env.
  try {
    return import.meta.env.VITE_API_URL || null;
  } catch {
    return null;
  }
}

/** Reject values that would make /api/* hit the static Hostinger SPA (HTML, not JSON). */
export function isUsableApiOrigin(url) {
  if (!url) return false;
  const raw = String(url).trim();
  if (!/^https?:\/\//i.test(raw)) return false;
  try {
    const host = new URL(raw).hostname.toLowerCase();
    if (host === 'agarwalglobalinvestments.com' || host === 'www.agarwalglobalinvestments.com') {
      return false;
    }
    if (host === 'localhost' || host === '127.0.0.1') return true;
    if (host.endsWith('.onrender.com')) return true;
    // Allow other explicit API hosts, but never the marketing site.
    return host.includes('api') || host.includes('backend') || host.includes('render');
  } catch {
    return false;
  }
}

const viteUrl = readViteApiUrl();

const runtimeOverride =
  typeof window !== 'undefined' && window.__API_ORIGIN
    ? String(window.__API_ORIGIN)
    : null;

const hostname =
  typeof window !== 'undefined' && window.location?.hostname
    ? window.location.hostname
    : null;

const runningLocally = hostname === 'localhost' || hostname === '127.0.0.1';

const productionApiFallback =
  hostname && /agarwalglobalinvestments\.com$/i.test(hostname) ? RENDER_API_ORIGIN : null;

export const API_ORIGIN =
  (isUsableApiOrigin(runtimeOverride) ? runtimeOverride.replace(/\/$/, '') : null) ||
  (isUsableApiOrigin(viteUrl) ? String(viteUrl).replace(/\/$/, '') : null) ||
  (runningLocally ? 'http://localhost:5000' : null) ||
  productionApiFallback;

export default API_ORIGIN;

if (runningLocally) {
  console.info('[config] API_ORIGIN =', API_ORIGIN);
}
